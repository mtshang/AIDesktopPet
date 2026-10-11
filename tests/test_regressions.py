"""Run with: .venv/Scripts/python.exe -m unittest discover -s tests -v"""
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
from json_write import save_config_atomic, update_config_atomic, validate_config_name

# Imports must never read or create files in the user's real API/config directories.
_import_root = tempfile.TemporaryDirectory()
with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(Path(_import_root.name) / "app.exe")):
    import bottom
    import pet
    import set_api
    import set_general
    import set_mod
    import set_peek
    import version_check
    import worker_lifecycle

app = QApplication.instance() or QApplication([])


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "api").mkdir()
        self.config = self.root / "config.json"
        save_config_atomic({"API_LAST": "", "PET_LAST": "default_pet", "IS_FIRST_RUN": False}, self.config)
        for module in (bottom, pet, set_api, set_peek, set_general):
            for attr, value in (("current_dir", str(self.root)), ("config_path", str(self.config))):
                if hasattr(module, attr):
                    p = patch.object(module, attr, value); p.start(); self.addCleanup(p.stop)
        p = patch.object(version_check, "CONFIG_PATH", str(self.root / "version.json"))
        p.start(); self.addCleanup(p.stop)
        bottom.global_config._init_vars()
        worker_lifecycle._registry = None
        for name in ("information", "warning", "question"):
            p = patch.object(QMessageBox, name, return_value=QMessageBox.Yes)
            p.start(); self.addCleanup(p.stop)

    def api(self, name, value="test-key"):
        payload = {"VISION_API_KEY": value, "CHAT_API_KEY": value,
                   "VISION_BASE_URL": "https://example.invalid/v1", "CHAT_BASE_URL": "https://example.invalid/v1",
                   "VISION_MODEL": "vision", "CHAT_MODEL": "chat"}
        save_config_atomic(payload, self.root / "api" / (name + ".json"))
        return payload

    def test_atomic_failure_preserves_original_and_reports_error(self):
        original = self.config.read_bytes()
        with patch("json_write.os.replace", side_effect=PermissionError("blocked")):
            with self.assertRaises(PermissionError):
                save_config_atomic({"lost": True}, self.config)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse(list(self.root.glob("*.tmp")))

    def test_parallel_updates_do_not_lose_fields(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda n: update_config_atomic(self.config, {str(n): n}), range(40)))
        data = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertTrue(all(data[str(n)] == n for n in range(40)))
        self.assertEqual(data["PET_LAST"], "default_pet")

    def test_relative_json_path(self):
        old = os.getcwd()
        try:
            os.chdir(self.root)
            save_config_atomic({"ok": True}, "relative.json")
        finally:
            os.chdir(old)
        self.assertTrue((self.root / "relative.json").exists())

    def test_api_name_rejects_paths_and_windows_reserved_names(self):
        for name in ("", "..", "../secret", "x/y", "x\\y", "CON", "NUL.txt", "bad.", "bad:"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_config_name(name)
        self.assertEqual(validate_config_name("配置1"), "配置1")

    def test_api_rename_write_failure_keeps_original(self):
        payload = self.api("old")
        worker = set_api.SaveApiWorker("old", "new", "old", str(self.root / "api"), str(self.config), payload)
        result = []; worker.finished_signal.connect(lambda *args: result.append(args))
        with patch.object(set_api, "save_config_atomic", side_effect=PermissionError("blocked")):
            worker.run()
        self.assertFalse(result[0][0])
        self.assertTrue((self.root / "api/old.json").exists())

    def test_api_rename_does_not_overwrite_another_config(self):
        old = self.api("old", "old-key"); self.api("new", "new-key")
        worker = set_api.SaveApiWorker("old", "new", "old", str(self.root / "api"), str(self.config), old)
        result=[]; worker.finished_signal.connect(lambda *args: result.append(args)); worker.run()
        self.assertFalse(result[0][0])
        self.assertEqual(json.loads((self.root / "api/new.json").read_text(encoding="utf-8"))["CHAT_API_KEY"], "new-key")
        self.assertTrue((self.root / "api/old.json").exists())

    def test_active_api_rename_and_delete_sync_runtime(self):
        payload = self.api("old")
        update_config_atomic(self.config, {"API_LAST": "old"})
        bottom.global_config.reload_api_config()
        page = set_api.ApiPage()
        worker = set_api.SaveApiWorker("old", "new", "old", str(self.root / "api"), str(self.config), payload)
        worker.run(); page.on_api_saved(True, "", "new")
        self.assertEqual(bottom.global_config.api_last, "new")
        self.assertEqual(page.active_api_name, "new")
        (self.root / "api/new.json").unlink()
        page.on_api_deleted(True, "")
        self.assertEqual(bottom.global_config.get_ai_payload()["c_key"], "")
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8"))["API_LAST"], "")
        page.close()

    def test_api_enable_updates_button_and_runtime(self):
        self.api("one"); self.api("two")
        update_config_atomic(self.config, {"API_LAST": "one"})
        page = set_api.ApiPage()
        set_api.EnableApiWorker(str(self.config), "two").run()
        page.on_api_enabled(True, "", "two")
        self.assertEqual(page.active_api_name, "two")
        self.assertEqual(bottom.global_config.api_last, "two")
        self.assertFalse(page.enable_api_btn.isEnabled())
        page.close()

    def test_new_character_does_not_inherit_previous_phrases(self):
        for name, data in (("one", {"chat_prompt": "one", "chat_example": ["private phrase"]}), ("two", {"chat_prompt": "two"})):
            folder=self.root / "petmod" / name; folder.mkdir(parents=True)
            save_config_atomic(data, folder / "nature.json")
            update_config_atomic(self.config, {"PET_LAST": name})
            bottom.global_config.reload_nature_config()
        self.assertEqual(bottom.global_config.get_ai_payload()["c_examples"], [])

    def test_model_requests_follow_user_prompt_and_token_limit(self):
        cfg=bottom.global_config
        cfg.chat_prompt="A user-selected persona"; cfg.chat_max_tokens=37; cfg.vision_max_tokens=19
        clients=[Mock(),Mock()]
        for client,content in zip(clients,["screen content","Hello 🐾"]):
            client.__enter__=Mock(return_value=client); client.__exit__=Mock(return_value=False)
            client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
        with patch.object(bottom,"OpenAI",side_effect=clients): result=bottom.get_ai_reply("fake-image")
        self.assertEqual(result,{"status":"success","reply":"Hello 🐾"})
        args=clients[1].chat.completions.create.call_args.kwargs
        self.assertEqual(args["messages"][0],{"role":"system","content":cfg.chat_prompt})
        self.assertEqual(args["max_tokens"],37)
        self.assertNotIn("response_format",args)
        self.assertEqual(clients[0].chat.completions.create.call_args.kwargs["max_tokens"],19)
        for client in clients: client.__exit__.assert_called_once()

    def test_network_failure_is_not_reported_as_success(self):
        with patch.object(bottom,"OpenAI",side_effect=RuntimeError("connection timeout")):
            result=bottom.get_ai_reply("fake-image")
        self.assertEqual(result["status"],"error")

    def test_version_comparison_is_numeric_and_only_newer_alerts(self):
        for current,remote,expected in (("v0.2.0","v0.1.9",False),("v0.2.0","v0.2.0",False),("v0.2.0","v0.10.0",True),("v0.2.0-rc.1","v0.2.0",True)):
            save_config_atomic({"current_version":current,"ignored_versions":[]},version_check.CONFIG_PATH)
            worker=version_check.VersionCheckThread(); result=[]; worker.update_found_signal.connect(result.append)
            with patch.object(worker,"fetch_latest_version",return_value=remote): worker.run()
            self.assertEqual(bool(result),expected,(current,remote))

    def test_emoji_bubble_and_taskbar_toggle(self):
        # Real widgets, but no global keyboard hook, tray icon, or API call.
        with patch.object(pet.PetWindow,"init_tray"), patch.object(pet.keyboard,"add_hotkey"), patch.object(pet,"start_worker"):
            window=pet.PetWindow()
            from PySide6.QtGui import QAction
            window.tray_hide_action=QAction(window)
            window.show_bubble("Hello 🐾 😀")
            self.assertGreater(window.bubble_time_left,0)
            window.toggle_taskbar()
            self.assertIn("✓",window.tray_hide_action.text())
            self.assertTrue(window.windowFlags() & Qt.WindowDoesNotAcceptFocus)
            window.peek_timer.stop(); window.loading_timer.stop(); window.bubble_timer.stop(); window.anim_timer.stop()
            window.hide(); window.bubble_win.hide()
            window.deleteLater(); window.bubble_win.deleteLater()

    def test_hotkey_capture_cancelled_on_hide(self):
        page=set_peek.PeekPage(); states=[]; page.recording_state_signal.connect(states.append)
        page.show(); app.processEvents()
        with patch.object(page,"grabKeyboard"), patch.object(page,"releaseKeyboard"):
            old=page.hk_display.text(); page.start_capturing_key(); page.hide()
        self.assertEqual(states,[True,False])
        self.assertEqual(page.hk_display.text(),old)
        self.assertFalse(page.is_capturing_key)
        page.close()

    def test_screenshot_delay_does_not_queue_multiple_captures(self):
        dummy=SimpleNamespace(ignore_hotkey=False,
            bubble_win=SimpleNamespace(is_waiting_for_ai=False,hide=Mock()),
            screenshot_thread=SimpleNamespace(isRunning=lambda:False),
            ai_thread=SimpleNamespace(isRunning=lambda:False),
            peek_timer=SimpleNamespace(stop=Mock()),hide=Mock())
        with patch.object(pet.QTimer,"singleShot") as schedule, patch.object(pet.QApplication,"processEvents"):
            pet.PetWindow.on_f9_pressed_safe(dummy)
            pet.PetWindow.on_f9_pressed_safe(dummy)
        self.assertEqual(schedule.call_count,1)

    def test_registry_keeps_worker_alive_and_waits_before_exit(self):
        class Job(QThread):
            def run(self): self.msleep(60)
        registry=worker_lifecycle.worker_registry(); drained=[]; registry.drained.connect(lambda:drained.append(True))
        job=Job(); self.assertTrue(registry.start(job))
        registry.begin_shutdown()
        self.assertFalse(registry.start(Job()))
        self.assertFalse(drained)
        deadline=time.monotonic()+3
        while not drained and time.monotonic()<deadline:
            app.processEvents(); time.sleep(0.005)
        self.assertTrue(drained)
        self.assertFalse(registry.workers)
        self.assertFalse(job.isRunning())
        worker_lifecycle._registry=None

    def test_source_autostart_quotes_interpreter_and_script(self):
        fake=SimpleNamespace()
        with patch.object(set_general.sys,"frozen",False,create=True), patch.object(set_general.sys,"executable",r"C:\Python Dir\python.exe"), patch.object(set_general,"get_base_path",return_value=r"C:\Project Dir"), patch.object(set_general.winreg,"OpenKey",return_value=MagicMock()), patch.object(set_general.winreg,"CloseKey"), patch.object(set_general.winreg,"SetValueEx") as set_value:
            self.assertTrue(set_general.GeneralPage.set_windows_autostart(fake,True))
        command=set_value.call_args.args[-1]
        self.assertEqual(command,'"C:\\Python Dir\\python.exe" "C:\\Project Dir\\main.py"')

    def test_shutdown_hides_ui_waits_and_saves_position(self):
        class Job(QThread):
            def run(self): self.msleep(60)
        registry=worker_lifecycle.worker_registry(); job=Job(); registry.start(job)
        dummy=SimpleNamespace()
        for name in ("peek_timer","loading_timer","anim_timer","bubble_timer"):
            setattr(dummy,name,SimpleNamespace(stop=Mock()))
        dummy.bubble_win=SimpleNamespace(hide=Mock(),busy_timer=SimpleNamespace(stop=Mock()))
        dummy.tray_icon=SimpleNamespace(hide=Mock()); dummy.settings_window=SimpleNamespace(hide=Mock())
        dummy.hide=Mock(); dummy.x=lambda:123; dummy.y=lambda:456
        dummy.finish_shutdown=lambda:pet.PetWindow.finish_shutdown(dummy)
        with patch.object(pet.keyboard,"unhook_all_hotkeys"), patch.object(app,"quit") as quit_app:
            pet.PetWindow.request_shutdown(dummy)
            dummy.hide.assert_called_once(); dummy.bubble_win.hide.assert_called_once()
            quit_app.assert_not_called()
            deadline=time.monotonic()+3
            while not quit_app.called and time.monotonic()<deadline:
                app.processEvents(); time.sleep(0.005)
            quit_app.assert_called_once()
        data=json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual((data["LAST_POS_X"],data["LAST_POS_Y"]),(123,456))
        worker_lifecycle._registry=None

    def test_registry_handles_workers_using_delete_later(self):
        class Job(QThread):
            def run(self): self.msleep(10)
        job=Job(); job.finished.connect(job.deleteLater)
        registry=worker_lifecycle.worker_registry(); done=[]; registry.drained.connect(lambda:done.append(True))
        registry.start(job); registry.begin_shutdown()
        deadline=time.monotonic()+3
        while not done and time.monotonic()<deadline:
            app.processEvents(); time.sleep(0.005)
        self.assertTrue(done)
        self.assertFalse(registry.workers)
        worker_lifecycle._registry=None

    def make_mod(self, name="one", base="petmod"):
        folder=self.root / base / name
        folder.mkdir(parents=True)
        nature=json.loads(json.dumps(set_mod.DEFAULT_NATURE_TEMPLATE))
        nature["name"]=name; nature["default_image"]="old.png"
        (folder / "old.png").write_bytes(b"old image")
        save_config_atomic(nature,folder / "nature.json")
        return folder,nature

    def mod_page(self):
        with patch.object(set_mod,"get_base_path",return_value=str(self.root)):
            page=set_mod.ModPage()
        self.addCleanup(page.close)
        return page

    def test_mod_image_is_only_deleted_after_successful_save(self):
        folder,nature=self.make_mod()
        update_config_atomic(self.config,{"PET_LAST":"one"})
        page=self.mod_page(); changes=[]; page.mod_applied_signal.connect(changes.append)
        (folder / "new.png").write_bytes(b"new image")
        page.on_image_copied(True,"",str(folder / "new.png"),"default","new.png")
        self.assertTrue((folder / "old.png").exists())
        self.assertEqual(json.loads((folder / "nature.json").read_text(encoding="utf-8"))["default_image"],"old.png")
        with patch.object(set_mod,"start_worker",side_effect=lambda worker:worker.run()):
            page.save_current_mod()
        self.assertFalse((folder / "old.png").exists())
        self.assertEqual(json.loads((folder / "nature.json").read_text(encoding="utf-8"))["default_image"],"new.png")
        self.assertEqual(changes,["one"])

    def test_unsaved_mod_image_edit_does_not_damage_saved_character(self):
        folder,_=self.make_mod(); self.make_mod("two")
        update_config_atomic(self.config,{"PET_LAST":"one"})
        page=self.mod_page()
        (folder / "new.png").write_bytes(b"new")
        page.on_image_copied(True,"",str(folder / "new.png"),"default","new.png")
        page.refresh_mod_list(target_folder="two")
        self.assertTrue((folder / "old.png").exists())
        self.assertFalse(page.pending_image_removals)
        self.assertEqual(json.loads((folder / "nature.json").read_text(encoding="utf-8"))["default_image"],"old.png")

    def test_same_name_image_import_does_not_overwrite_saved_image(self):
        folder,_=self.make_mod()
        source=self.root / "old.png"; source.write_bytes(b"replacement")
        worker=set_mod.CopyWorker(str(source),str(folder / "old.png"),"default","old.png")
        results=[]; worker.finished_signal.connect(lambda *args:results.append(args)); worker.run()
        self.assertTrue(results[0][0])
        self.assertNotEqual(results[0][4],"old.png")
        self.assertEqual((folder / "old.png").read_bytes(),b"old image")
        self.assertEqual(Path(results[0][2]).read_bytes(),b"replacement")

    def test_mod_save_failure_preserves_old_image_and_config(self):
        import mod_storage
        folder,nature=self.make_mod(); original=(folder / "nature.json").read_bytes()
        nature["default_image"]="new.png"; (folder / "new.png").write_bytes(b"new")
        with patch.object(mod_storage,"save_config_atomic",side_effect=PermissionError("blocked")):
            with self.assertRaises(PermissionError):
                mod_storage.save_mod(str(folder),str(folder),nature,str(folder.parent),str(self.config),{"old.png"})
        self.assertTrue((folder / "old.png").exists())
        self.assertEqual((folder / "nature.json").read_bytes(),original)

    def test_shared_animation_image_is_not_deleted(self):
        import mod_storage
        folder,nature=self.make_mod(); (folder / "standing").mkdir()
        shared=folder / "standing/shared.png"; shared.write_bytes(b"shared")
        nature["file"]["standing"]["frame"]=["shared.png"]
        mod_storage.save_mod(str(folder),str(folder),nature,str(folder.parent),str(self.config),{"standing/shared.png"})
        self.assertTrue(shared.exists())

    def test_active_mod_rename_preserves_activation_and_refreshes_ui(self):
        folder,_=self.make_mod(); update_config_atomic(self.config,{"PET_LAST":"one","OTHER":123})
        page=self.mod_page(); changes=[]; page.mod_applied_signal.connect(changes.append)
        page.mod_folder_input.setText("renamed")
        with patch.object(set_mod,"start_worker",side_effect=lambda worker:worker.run()):
            page.save_current_mod()
        config=json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(config["PET_LAST"],"renamed")
        self.assertEqual(config["OTHER"],123)
        self.assertEqual(changes,["renamed"])
        self.assertFalse(folder.exists())
        self.assertTrue((folder.parent / "renamed/nature.json").exists())

    def test_inactive_mod_rename_does_not_change_active_character(self):
        import mod_storage
        folder,nature=self.make_mod(); update_config_atomic(self.config,{"PET_LAST":"other"})
        mod_storage.save_mod(str(folder),str(folder.parent / "renamed"),nature,str(folder.parent),str(self.config),set())
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8"))["PET_LAST"],"other")

    def test_mod_rename_config_failure_rolls_back_folder_and_images(self):
        import mod_storage
        folder,nature=self.make_mod(); previous=json.loads((folder / "nature.json").read_text(encoding="utf-8"))
        nature["default_image"]="new.png"; (folder / "new.png").write_bytes(b"new")
        with patch.object(mod_storage,"update_config_atomic",side_effect=PermissionError("blocked")):
            with self.assertRaises(PermissionError):
                mod_storage.save_mod(str(folder),str(folder.parent / "renamed"),nature,str(folder.parent),str(self.config),{"old.png"})
        self.assertTrue((folder / "old.png").exists())
        self.assertFalse((folder.parent / "renamed").exists())
        self.assertEqual(json.loads((folder / "nature.json").read_text(encoding="utf-8")),previous)

    def test_deleting_active_mod_selects_default_and_notifies_pet(self):
        folder,_=self.make_mod(); self.make_mod("default_pet","asset/pet")
        update_config_atomic(self.config,{"PET_LAST":"one"})
        page=self.mod_page(); changes=[]; page.mod_applied_signal.connect(changes.append)
        with patch.object(set_mod,"start_worker",side_effect=lambda worker:worker.run()):
            page.delete_current_mod()
        self.assertFalse(folder.exists())
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8"))["PET_LAST"],"default_pet")
        self.assertEqual(changes,["default_pet"])
        self.assertEqual(page.current_mod_folder,"default_pet")

    def test_deleting_inactive_mod_keeps_active_character(self):
        folder,_=self.make_mod(); update_config_atomic(self.config,{"PET_LAST":"other"})
        worker=set_mod.DeleteWorker(str(folder),str(folder.parent),str(self.config)); result=[]
        worker.finished_signal.connect(lambda *args:result.append(args)); worker.run()
        self.assertEqual(result,[(True,"","")])
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8"))["PET_LAST"],"other")

    def test_delete_config_write_failure_does_not_remove_character(self):
        folder,_=self.make_mod(); update_config_atomic(self.config,{"PET_LAST":"one"})
        worker=set_mod.DeleteWorker(str(folder),str(folder.parent),str(self.config)); result=[]
        worker.finished_signal.connect(lambda *args:result.append(args))
        with patch.object(set_mod,"update_config_atomic",side_effect=PermissionError("blocked")):
            worker.run()
        self.assertFalse(result[0][0]); self.assertEqual(result[0][2],"")
        self.assertTrue(folder.exists())
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8"))["PET_LAST"],"one")

    def test_mod_cleanup_rejects_files_outside_character(self):
        import mod_storage
        folder,nature=self.make_mod(); outside=self.root / "outside.png"; outside.write_bytes(b"keep")
        with self.assertRaises(ValueError):
            mod_storage.save_mod(str(folder),str(folder),nature,str(folder.parent),str(self.config),{"../../outside.png"})
        self.assertTrue(outside.exists())
