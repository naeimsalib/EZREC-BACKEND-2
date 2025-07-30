before doing the Quick fix commands 

michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ sudo journalctl -u ezrec-api.service --no-pager -n 20
Jul 30 00:00:12 raspberrypi uvicorn[31541]:   File "<frozen importlib._bootstrap>", line 1149, in _find_and_load_unlocked
Jul 30 00:00:12 raspberrypi uvicorn[31541]:   File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
Jul 30 00:00:12 raspberrypi uvicorn[31541]:   File "<frozen importlib._bootstrap_external>", line 940, in exec_module
Jul 30 00:00:12 raspberrypi uvicorn[31541]:   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
Jul 30 00:00:12 raspberrypi uvicorn[31541]:   File "/opt/ezrec-backend/api/api_server.py", line 1, in <module>
Jul 30 00:00:12 raspberrypi uvicorn[31541]:     from booking_utils import update_booking_status
Jul 30 00:00:12 raspberrypi uvicorn[31541]:   File "/opt/ezrec-backend/api/booking_utils.py", line 17, in <module>
Jul 30 00:00:12 raspberrypi uvicorn[31541]:     supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
Jul 30 00:00:12 raspberrypi uvicorn[31541]:                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:00:12 raspberrypi uvicorn[31541]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
Jul 30 00:00:12 raspberrypi uvicorn[31541]:     return SyncClient.create(
Jul 30 00:00:12 raspberrypi uvicorn[31541]:            ^^^^^^^^^^^^^^^^^^
Jul 30 00:00:12 raspberrypi uvicorn[31541]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 30 00:00:12 raspberrypi uvicorn[31541]:     client = cls(supabase_url, supabase_key, options)
Jul 30 00:00:12 raspberrypi uvicorn[31541]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:00:12 raspberrypi uvicorn[31541]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
Jul 30 00:00:12 raspberrypi uvicorn[31541]:     raise SupabaseException("supabase_key is required")
Jul 30 00:00:12 raspberrypi uvicorn[31541]: supabase._sync.client.SupabaseException: supabase_key is required
Jul 30 00:00:12 raspberrypi systemd[1]: ezrec-api.service: Main process exited, code=exited, status=1/FAILURE
Jul 30 00:00:12 raspberrypi systemd[1]: ezrec-api.service: Failed with result 'exit-code'.
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ sudo journalctl -u dual_recorder.service --no-pager -n 20
Jul 30 00:00:22 raspberrypi systemd[1]: dual_recorder.service: Scheduled restart job, restart counter is at 126.
Jul 30 00:00:22 raspberrypi systemd[1]: Stopped dual_recorder.service - EZREC Dual Camera Recorder Service.
Jul 30 00:00:22 raspberrypi systemd[1]: Started dual_recorder.service - EZREC Dual Camera Recorder Service.
Jul 30 00:00:23 raspberrypi python3[31560]: Traceback (most recent call last):
Jul 30 00:00:23 raspberrypi python3[31560]:   File "/opt/ezrec-backend/backend/dual_recorder.py", line 77, in <module>
Jul 30 00:00:23 raspberrypi python3[31560]:     from booking_utils import update_booking_status
Jul 30 00:00:23 raspberrypi python3[31560]:   File "/opt/ezrec-backend/api/booking_utils.py", line 17, in <module>
Jul 30 00:00:23 raspberrypi python3[31560]:     supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
Jul 30 00:00:23 raspberrypi python3[31560]:                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:00:23 raspberrypi python3[31560]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
Jul 30 00:00:23 raspberrypi python3[31560]:     return SyncClient.create(
Jul 30 00:00:23 raspberrypi python3[31560]:            ^^^^^^^^^^^^^^^^^^
Jul 30 00:00:23 raspberrypi python3[31560]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 30 00:00:23 raspberrypi python3[31560]:     client = cls(supabase_url, supabase_key, options)
Jul 30 00:00:23 raspberrypi python3[31560]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:00:23 raspberrypi python3[31560]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
Jul 30 00:00:23 raspberrypi python3[31560]:     raise SupabaseException("supabase_key is required")
Jul 30 00:00:23 raspberrypi python3[31560]: supabase._sync.client.SupabaseException: supabase_key is required
Jul 30 00:00:23 raspberrypi systemd[1]: dual_recorder.service: Main process exited, code=exited, status=1/FAILURE
Jul 30 00:00:23 raspberrypi systemd[1]: dual_recorder.service: Failed with result 'exit-code'.
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ python3 -c "import kms; print('pykms available')" 2>/dev/null || echo "pykms not available"
pykms not available
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ apt search python3-kms
apt search pykms
Sorting... Done
Full Text Search... Done
python3-kms++/stable,now 0~git20231115~065257+9ae90ce-1 arm64 [installed]
  C++ library for kernel mode setting - python3 bindings

python3-kms++-dbgsym/stable 0~git20231115~065257+9ae90ce-1 arm64
  debug symbols for python3-kms++

Sorting... Done
Full Text Search... Done
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ cd /opt/ezrec-backend/backend
source venv/bin/activate
python3 -c "import picamera2; print('picamera2 import successful')"
Traceback (most recent call last):
  File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/picamera2/previews/drm_preview.py", line 9, in <module>
    import kms as pykms
ModuleNotFoundError: No module named 'kms'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/picamera2/__init__.py", line 11, in <module>
    from .picamera2 import Picamera2, Preview
  File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/picamera2/picamera2.py", line 32, in <module>
    from picamera2.previews import DrmPreview, NullPreview, QtGlPreview, QtPreview
  File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/picamera2/previews/__init__.py", line 1, in <module>
    from .drm_preview import DrmPreview
  File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/picamera2/previews/drm_preview.py", line 11, in <module>
    import pykms
ModuleNotFoundError: No module named 'pykms'
(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/backend $ cd /opt/ezrec-backend/api
source venv/bin/activate
python3 -c "import api_server; print('api_server import successful')"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/opt/ezrec-backend/api/api_server.py", line 1, in <module>
    from booking_utils import update_booking_status
  File "/opt/ezrec-backend/api/booking_utils.py", line 17, in <module>
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
    return SyncClient.create(
           ^^^^^^^^^^^^^^^^^^
  File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
    client = cls(supabase_url, supabase_key, options)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
    raise SupabaseException("supabase_key is required")
supabase._sync.client.SupabaseException: supabase_key is required
(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/api $ deactivate
michomanoly14892@raspberrypi:/opt/ezrec-backend/api $ cd /opt/ezrec-backend/api
source venv/bin/activate
python3 -c "import api_server; print('api_server import successful')"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/opt/ezrec-backend/api/api_server.py", line 1, in <module>
    from booking_utils import update_booking_status
  File "/opt/ezrec-backend/api/booking_utils.py", line 17, in <module>
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
    return SyncClient.create(
           ^^^^^^^^^^^^^^^^^^
  File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
    client = cls(supabase_url, supabase_key, options)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
    raise SupabaseException("supabase_key is required")
supabase._sync.client.SupabaseException: supabase_key is required
(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/api $ ls -la /opt/ezrec-backend/api/
ls -la /opt/ezrec-backend/backend/
total 76
drwxr-xr-x  6 ezrec ezrec  4096 Jul 29 23:37 .
drwxr-xr-x 19 ezrec ezrec  4096 Jul 29 23:37 ..
-rwxr-xr-x  1 ezrec ezrec 42432 Jul 29 23:37 api_server.py
-rwxr-xr-x  1 ezrec ezrec  2398 Jul 29 23:34 booking_utils.py
drwxr-xr-x  2 ezrec ezrec  4096 Jul 29 23:36 local_data
-rwxr-xr-x  1 ezrec ezrec   717 Jul 29 23:34 monitor.py
drwxr-xr-x  2 ezrec ezrec  4096 Jul 29 23:37 __pycache__
drwxr-xr-x  2 ezrec ezrec  4096 Jul 29 23:34 templates
drwxr-xr-x  5 ezrec ezrec  4096 Jul 29 23:34 venv
total 368
drwxr-xr-x  4 ezrec ezrec  4096 Jul 29 23:36 .
drwxr-xr-x 19 ezrec ezrec  4096 Jul 29 23:37 ..
-rwxr-xr-x  1 ezrec ezrec 12070 Jul 29 23:34 booking_manager.py
-rwxr-xr-x  1 ezrec ezrec 13191 Jul 29 23:34 camera_health_check.py
-rwxr-xr-x  1 ezrec ezrec 23676 Jul 29 23:34 camera_test_suite.py
-rwxr-xr-x  1 ezrec ezrec 13428 Jul 29 23:34 camera_test_web.py
-rwxr-xr-x  1 ezrec ezrec 23114 Jul 29 23:34 cleanup_old_data.py
-rwxr-xr-x  1 ezrec ezrec  3344 Jul 29 23:34 create_assets.py
-rwxr-xr-x  1 ezrec ezrec 68903 Jul 29 23:34 dual_recorder.py
-rwxr-xr-x  1 ezrec ezrec 21646 Jul 29 23:34 enhanced_merge.py
-rwxr-xr-x  1 ezrec ezrec  3386 Jul 29 23:34 enhanced_merge_test.py
drwxr-xr-x  2 ezrec ezrec  4096 Jul 29 23:37 __pycache__
-rwxr-xr-x  1 ezrec ezrec  5515 Jul 29 23:34 quick_camera_test.py
-rwxr-xr-x  1 ezrec ezrec  4164 Jul 29 23:34 refresh_user_media_simple.py
-rwxr-xr-x  1 ezrec ezrec 11522 Jul 29 23:34 smoke_test.py
-rwxr-xr-x  1 ezrec ezrec 21402 Jul 29 23:34 system_status.py
-rwxr-xr-x  1 ezrec ezrec  1027 Jul 29 23:34 test_camera_detection.py
-rwxr-xr-x  1 ezrec ezrec  1279 Jul 29 23:34 test_camera_fix.py
-rwxr-xr-x  1 ezrec ezrec  4704 Jul 29 23:34 test_cleanup.py
-rwxr-xr-x  1 ezrec ezrec  6351 Jul 29 23:34 test_simple.py
-rwxr-xr-x  1 ezrec ezrec 10018 Jul 29 23:34 test_system_health.py
-rwxr-xr-x  1 ezrec ezrec  6358 Jul 29 23:34 test_system_readiness.py
-rwxr-xr-x  1 ezrec ezrec 10756 Jul 29 23:34 test_system_status.py
drwxr-xr-x  5 ezrec ezrec  4096 Jul 29 23:36 venv
-rwxr-xr-x  1 ezrec ezrec 52368 Jul 29 23:34 video_worker.py
(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/api $ ls -la /opt/ezrec-backend/api/local_data/
ls -la /opt/ezrec-backend/backend/venv/
total 12
drwxr-xr-x 2 ezrec ezrec 4096 Jul 29 23:36 .
drwxr-xr-x 6 ezrec ezrec 4096 Jul 29 23:37 ..
-rw-rw-r-- 1 ezrec ezrec    3 Jul 29 23:37 bookings.json
total 24
drwxr-xr-x 5 ezrec ezrec 4096 Jul 29 23:36 .
drwxr-xr-x 4 ezrec ezrec 4096 Jul 29 23:36 ..
drwxr-xr-x 3 ezrec ezrec 4096 Jul 29 23:37 bin
drwxr-xr-x 3 ezrec ezrec 4096 Jul 29 23:36 include
drwxr-xr-x 3 ezrec ezrec 4096 Jul 29 23:36 lib
lrwxrwxrwx 1 ezrec ezrec    3 Jul 29 23:36 lib64 -> lib
-rw-r--r-- 1 ezrec ezrec  170 Jul 29 23:36 pyvenv.cfg
(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/api $ 

After doing the quick fix commnads

(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/api $ sudo apt update
sudo apt install -y python3-kms || sudo apt install -y python3-pykms || echo "pykms not available in repos"
Hit:1 http://deb.debian.org/debian bookworm InRelease
Hit:2 http://deb.debian.org/debian-security bookworm-security InRelease
Hit:3 http://deb.debian.org/debian bookworm-updates InRelease                     
Hit:4 http://archive.raspberrypi.com/debian bookworm InRelease                    
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
All packages are up to date.
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
E: Unable to locate package python3-kms
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
E: Unable to locate package python3-pykms
pykms not available in repos
(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/api $ cd /opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/
sudo touch kms.py
sudo echo "print('kms module placeholder')" > kms.py
sudo chown ezrec:ezrec kms.py
bash: kms.py: Permission denied
(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages $ cd /opt/ezrec-backend/api
source venv/bin/activate
python3 -c "from api_server import app; print('API server loads successfully')"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/opt/ezrec-backend/api/api_server.py", line 1, in <module>
    from booking_utils import update_booking_status
  File "/opt/ezrec-backend/api/booking_utils.py", line 17, in <module>
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
    return SyncClient.create(
           ^^^^^^^^^^^^^^^^^^
  File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
    client = cls(supabase_url, supabase_key, options)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
    raise SupabaseException("supabase_key is required")
supabase._sync.client.SupabaseException: supabase_key is required
(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/api $ sudo systemctl restart ezrec-api.service
sudo systemctl status ezrec-api.service
sudo journalctl -u ezrec-api.service -f
● ezrec-api.service - EZREC FastAPI Backend
     Loaded: loaded (/etc/systemd/system/ezrec-api.service; enabled; preset: enabled)
     Active: active (running) since Wed 2025-07-30 00:01:49 EDT; 20ms ago
   Main PID: 32113 (uvicorn)
      Tasks: 1 (limit: 9572)
        CPU: 17ms
     CGroup: /system.slice/ezrec-api.service
             └─32113 /opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/api/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000

Jul 30 00:01:49 raspberrypi systemd[1]: Started ezrec-api.service - EZREC FastAPI Backend.
Jul 30 00:01:48 raspberrypi uvicorn[32096]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 30 00:01:48 raspberrypi uvicorn[32096]:     client = cls(supabase_url, supabase_key, options)
Jul 30 00:01:48 raspberrypi uvicorn[32096]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:48 raspberrypi uvicorn[32096]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
Jul 30 00:01:48 raspberrypi uvicorn[32096]:     raise SupabaseException("supabase_key is required")
Jul 30 00:01:48 raspberrypi uvicorn[32096]: supabase._sync.client.SupabaseException: supabase_key is required
Jul 30 00:01:48 raspberrypi systemd[1]: ezrec-api.service: Main process exited, code=exited, status=1/FAILURE
Jul 30 00:01:48 raspberrypi systemd[1]: ezrec-api.service: Failed with result 'exit-code'.
Jul 30 00:01:49 raspberrypi systemd[1]: Stopped ezrec-api.service - EZREC FastAPI Backend.
Jul 30 00:01:49 raspberrypi systemd[1]: Started ezrec-api.service - EZREC FastAPI Backend.
Jul 30 00:01:50 raspberrypi uvicorn[32113]: Traceback (most recent call last):
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/bin/uvicorn", line 8, in <module>
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     sys.exit(main())
Jul 30 00:01:50 raspberrypi uvicorn[32113]:              ^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 1442, in __call__
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     return self.main(*args, **kwargs)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 1363, in main
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     rv = self.invoke(ctx)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:          ^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 1226, in invoke
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     return ctx.invoke(self.callback, **ctx.params)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 794, in invoke
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     return callback(*args, **kwargs)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:            ^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/main.py", line 413, in main
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     run(
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/main.py", line 580, in run
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     server.run()
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 67, in run
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     return asyncio.run(self.serve(sockets=sockets))
Jul 30 00:01:50 raspberrypi uvicorn[32113]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/usr/lib/python3.11/asyncio/runners.py", line 190, in run
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     return runner.run(main)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:            ^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/usr/lib/python3.11/asyncio/runners.py", line 118, in run
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     return self._loop.run_until_complete(task)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/usr/lib/python3.11/asyncio/base_events.py", line 653, in run_until_complete
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     return future.result()
Jul 30 00:01:50 raspberrypi uvicorn[32113]:            ^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 71, in serve
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     await self._serve(sockets)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 78, in _serve
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     config.load()
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/config.py", line 436, in load
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     self.loaded_app = import_from_string(self.app)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/importer.py", line 19, in import_from_string
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     module = importlib.import_module(module_str)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/usr/lib/python3.11/importlib/__init__.py", line 126, in import_module
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     return _bootstrap._gcd_import(name[level:], package, level)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "<frozen importlib._bootstrap>", line 1206, in _gcd_import
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "<frozen importlib._bootstrap>", line 1178, in _find_and_load
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "<frozen importlib._bootstrap>", line 1149, in _find_and_load_unlocked
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "<frozen importlib._bootstrap_external>", line 940, in exec_module
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/api_server.py", line 1, in <module>
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     from booking_utils import update_booking_status
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/booking_utils.py", line 17, in <module>
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     return SyncClient.create(
Jul 30 00:01:50 raspberrypi uvicorn[32113]:            ^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     client = cls(supabase_url, supabase_key, options)
Jul 30 00:01:50 raspberrypi uvicorn[32113]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 30 00:01:50 raspberrypi uvicorn[32113]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
Jul 30 00:01:50 raspberrypi uvicorn[32113]:     raise SupabaseException("supabase_key is required")
Jul 30 00:01:50 raspberrypi uvicorn[32113]: supabase._sync.client.SupabaseException: supabase_key is required
Jul 30 00:01:50 raspberrypi systemd[1]: ezrec-api.service: Main process exited, code=exited, status=1/FAILURE
Jul 30 00:01:50 raspberrypi systemd[1]: ezrec-api.service: Failed with result 'exit-code'.
^C
(venv) michomanoly14892@raspberrypi:/opt/ezrec-backend/api $ 