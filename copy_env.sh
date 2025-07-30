michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ git pull
remote: Enumerating objects: 9, done.
remote: Counting objects: 100% (9/9), done.
remote: Compressing objects: 100% (3/3), done.
remote: Total 6 (delta 3), reused 6 (delta 3), pack-reused 0 (from 0)
Unpacking objects: 100% (6/6), 20.93 KiB | 714.00 KiB/s, done.
From https://github.com/naeimsalib/EZREC-BACKEND-2
   5f3421b..1ffe371  main       -> origin/main
Updating 5f3421b..1ffe371
Fast-forward
 deployment.sh           |   4 ++
 fix_venv.sh             |  66 ++++++++++++++++++++++++++
 logs.txt                | 503 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--------------------
 test_complete_system.py | 312 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 4 files changed, 835 insertions(+), 50 deletions(-)
 create mode 100644 fix_venv.sh
 create mode 100644 test_complete_system.py
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ ./deployment.sh 
🚀 EZREC Backend Deployment Script
==================================
🛑 Stopping all existing services...
🔪 Killing remaining processes...
🧹 Cleaning up old installation...
📁 Removing old installation...
📁 Copying project files...
🔧 Checking and installing required tools...
✅ FFmpeg is available
✅ FFprobe is available
✅ v4l2-ctl is available
✅ Picamera2 is available
📦 Installing additional dependencies...
Hit:1 http://deb.debian.org/debian bookworm InRelease
Hit:2 http://deb.debian.org/debian-security bookworm-security InRelease
Hit:3 http://deb.debian.org/debian bookworm-updates InRelease
Hit:4 http://archive.raspberrypi.com/debian bookworm InRelease
Reading package lists... Done                               
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
python3-requests is already the newest version (2.28.1+dfsg-1).
python3-psutil is already the newest version (5.9.4-1+b1).
python3-boto3 is already the newest version (1.26.27+dfsg-1).
python3-dotenv is already the newest version (0.21.0-1).
build-essential is already the newest version (12.9).
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
imagemagick is already the newest version (8:6.9.11.60+dfsg-1.6+deb12u3).
v4l-utils is already the newest version (1.22.1-5+b2).
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
📁 Creating required directories...
🔐 Creating dedicated user and fixing permissions...
✅ ezrec user already exists
🔐 Setting ownership to current user for virtual environment creation...
🐍 Setting up Python environments...
🐍 Setting up API virtual environment...
📦 Creating API virtual environment...
📦 Installing API dependencies...
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Requirement already satisfied: pip in ./venv/lib/python3.11/site-packages (23.0.1)
Collecting pip
  Using cached pip-25.1.1-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 23.0.1
    Uninstalling pip-23.0.1:
      Successfully uninstalled pip-23.0.1
Successfully installed pip-25.1.1
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Collecting fastapi==0.116.1 (from -r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached fastapi-0.116.1-py3-none-any.whl.metadata (28 kB)
Collecting uvicorn==0.35.0 (from -r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached uvicorn-0.35.0-py3-none-any.whl.metadata (6.5 kB)
Collecting python-multipart==0.0.20 (from -r /opt/ezrec-backend/requirements.txt (line 4))
  Using cached https://www.piwheels.org/simple/python-multipart/python_multipart-0.0.20-py3-none-any.whl (24 kB)
Collecting jinja2==3.1.2 (from -r /opt/ezrec-backend/requirements.txt (line 5))
  Using cached https://www.piwheels.org/simple/jinja2/Jinja2-3.1.2-py3-none-any.whl (133 kB)
Collecting starlette==0.47.2 (from -r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached starlette-0.47.2-py3-none-any.whl.metadata (6.2 kB)
Collecting supabase==2.16.0 (from -r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached supabase-2.16.0-py3-none-any.whl.metadata (10 kB)
Collecting pyjwt<3.0.0,>=2.10.1 (from -r /opt/ezrec-backend/requirements.txt (line 10))
  Using cached https://www.piwheels.org/simple/pyjwt/PyJWT-2.10.1-py3-none-any.whl (22 kB)
Collecting boto3==1.39.14 (from -r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached boto3-1.39.14-py3-none-any.whl.metadata (6.7 kB)
Collecting psutil==5.9.5 (from -r /opt/ezrec-backend/requirements.txt (line 16))
  Using cached psutil-5.9.5-cp311-abi3-linux_aarch64.whl
Collecting python-dotenv==1.0.0 (from -r /opt/ezrec-backend/requirements.txt (line 17))
  Using cached https://www.piwheels.org/simple/python-dotenv/python_dotenv-1.0.0-py3-none-any.whl (19 kB)
Collecting requests==2.31.0 (from -r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached https://www.piwheels.org/simple/requests/requests-2.31.0-py3-none-any.whl (62 kB)
  DEPRECATION: Wheel filename 'pytz-2013d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2013d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012j-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012j-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012h-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012h-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012g-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012g-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012f-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012f-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011n-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011n-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011k-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011k-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011j-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011j-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011h-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011h-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011g-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011g-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011e-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011e-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
Collecting pytz==2025.2 (from -r /opt/ezrec-backend/requirements.txt (line 19))
  Using cached https://www.piwheels.org/simple/pytz/pytz-2025.2-py3-none-any.whl (509 kB)
Collecting email-validator==2.2.0 (from -r /opt/ezrec-backend/requirements.txt (line 22))
  Using cached https://www.piwheels.org/simple/email-validator/email_validator-2.2.0-py3-none-any.whl (33 kB)
Collecting opencv-python-headless==4.12.0.88 (from -r /opt/ezrec-backend/requirements.txt (line 25))
  Using cached opencv_python_headless-4.12.0.88-cp37-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl.metadata (19 kB)
Collecting picamera2==0.3.30 (from -r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached picamera2-0.3.30-py3-none-any.whl.metadata (6.4 kB)
Collecting simplejpeg==1.8.2 (from -r /opt/ezrec-backend/requirements.txt (line 27))
  Using cached simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (32 kB)
Collecting numpy<2.3.0,>=2.0.0 (from -r /opt/ezrec-backend/requirements.txt (line 30))
  Using cached numpy-2.2.6-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (63 kB)
Collecting python-dateutil==2.9.0.post0 (from -r /opt/ezrec-backend/requirements.txt (line 33))
  Using cached https://www.piwheels.org/simple/python-dateutil/python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
Collecting portalocker==2.7.0 (from -r /opt/ezrec-backend/requirements.txt (line 36))
  Using cached https://www.piwheels.org/simple/portalocker/portalocker-2.7.0-py2.py3-none-any.whl (15 kB)
Collecting dataclasses-json==0.6.4 (from -r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached https://archive1.piwheels.org/simple/dataclasses-json/dataclasses_json-0.6.4-py3-none-any.whl (28 kB)
Collecting pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4 (from fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached pydantic-2.11.7-py3-none-any.whl.metadata (67 kB)
Collecting typing-extensions>=4.8.0 (from fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached typing_extensions-4.14.1-py3-none-any.whl.metadata (3.0 kB)
Collecting anyio<5,>=3.6.2 (from starlette==0.47.2->-r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached https://www.piwheels.org/simple/anyio/anyio-4.9.0-py3-none-any.whl (100 kB)
Collecting click>=7.0 (from uvicorn==0.35.0->-r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached click-8.2.1-py3-none-any.whl.metadata (2.5 kB)
Collecting h11>=0.8 (from uvicorn==0.35.0->-r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting MarkupSafe>=2.0 (from jinja2==3.1.2->-r /opt/ezrec-backend/requirements.txt (line 5))
  Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.0 kB)
Collecting gotrue<3.0.0,>=2.11.0 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached gotrue-2.12.3-py3-none-any.whl.metadata (6.5 kB)
Collecting httpx<0.29,>=0.26 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/httpx/httpx-0.28.1-py3-none-any.whl (73 kB)
Collecting postgrest<1.2,>0.19 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached postgrest-1.1.1-py3-none-any.whl.metadata (3.5 kB)
Collecting realtime<2.6.0,>=2.4.0 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached realtime-2.5.3-py3-none-any.whl.metadata (6.7 kB)
Collecting storage3<0.13,>=0.10 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached storage3-0.12.0-py3-none-any.whl.metadata (1.9 kB)
Collecting supafunc<0.11,>=0.9 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached supafunc-0.10.1-py3-none-any.whl.metadata (1.2 kB)
Collecting botocore<1.40.0,>=1.39.14 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached botocore-1.39.16-py3-none-any.whl.metadata (5.7 kB)
Collecting jmespath<2.0.0,>=0.7.1 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached https://www.piwheels.org/simple/jmespath/jmespath-1.0.1-py3-none-any.whl (20 kB)
Collecting s3transfer<0.14.0,>=0.13.0 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached s3transfer-0.13.1-py3-none-any.whl.metadata (1.7 kB)
Collecting charset-normalizer<4,>=2 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (35 kB)
Collecting idna<4,>=2.5 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached https://www.piwheels.org/simple/idna/idna-3.10-py3-none-any.whl (70 kB)
Collecting urllib3<3,>=1.21.1 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached urllib3-2.5.0-py3-none-any.whl.metadata (6.5 kB)
Collecting certifi>=2017.4.17 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached certifi-2025.7.14-py3-none-any.whl.metadata (2.4 kB)
Collecting dnspython>=2.0.0 (from email-validator==2.2.0->-r /opt/ezrec-backend/requirements.txt (line 22))
  Using cached https://www.piwheels.org/simple/dnspython/dnspython-2.7.0-py3-none-any.whl (313 kB)
Collecting PiDNG (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached pidng-4.0.9-cp311-cp311-linux_aarch64.whl
Collecting av (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl.metadata (4.6 kB)
Collecting jsonschema (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached jsonschema-4.25.0-py3-none-any.whl.metadata (7.7 kB)
Collecting libarchive-c (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached libarchive_c-5.3-py3-none-any.whl.metadata (5.8 kB)
Collecting piexif (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/piexif/piexif-1.1.3-py2.py3-none-any.whl (20 kB)
Collecting pillow (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl.metadata (9.0 kB)
Collecting python-prctl (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached python_prctl-1.8.1-cp311-cp311-linux_aarch64.whl
Collecting tqdm (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/tqdm/tqdm-4.67.1-py3-none-any.whl (78 kB)
Collecting videodev2 (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached videodev2-0.0.4-py3-none-any.whl.metadata (2.8 kB)
Collecting six>=1.5 (from python-dateutil==2.9.0.post0->-r /opt/ezrec-backend/requirements.txt (line 33))
  Using cached https://www.piwheels.org/simple/six/six-1.17.0-py2.py3-none-any.whl (11 kB)
Collecting marshmallow<4.0.0,>=3.18.0 (from dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached https://www.piwheels.org/simple/marshmallow/marshmallow-3.26.1-py3-none-any.whl (50 kB)
Collecting typing-inspect<1,>=0.4.0 (from dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached https://www.piwheels.org/simple/typing-inspect/typing_inspect-0.9.0-py3-none-any.whl (8.8 kB)
Collecting sniffio>=1.1 (from anyio<5,>=3.6.2->starlette==0.47.2->-r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached https://www.piwheels.org/simple/sniffio/sniffio-1.3.1-py3-none-any.whl (10 kB)
Collecting httpcore==1.* (from httpx<0.29,>=0.26->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting h2<5,>=3 (from httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/h2/h2-4.2.0-py3-none-any.whl (60 kB)
Collecting hyperframe<7,>=6.1 (from h2<5,>=3->httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/hyperframe/hyperframe-6.1.0-py3-none-any.whl (13 kB)
Collecting hpack<5,>=4.1 (from h2<5,>=3->httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/hpack/hpack-4.1.0-py3-none-any.whl (34 kB)
Collecting packaging>=17.0 (from marshmallow<4.0.0,>=3.18.0->dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached packaging-25.0-py3-none-any.whl.metadata (3.3 kB)
Collecting deprecation<3.0.0,>=2.1.0 (from postgrest<1.2,>0.19->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/deprecation/deprecation-2.1.0-py2.py3-none-any.whl (11 kB)
Collecting annotated-types>=0.6.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached https://www.piwheels.org/simple/annotated-types/annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting pydantic-core==2.33.2 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached pydantic_core-2.33.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.8 kB)
Collecting typing-inspection>=0.4.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached typing_inspection-0.4.1-py3-none-any.whl.metadata (2.6 kB)
Collecting websockets<16,>=11 (from realtime<2.6.0,>=2.4.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached websockets-15.0.1-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.8 kB)
Collecting strenum<0.5.0,>=0.4.15 (from supafunc<0.11,>=0.9->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/strenum/StrEnum-0.4.15-py3-none-any.whl (8.9 kB)
Collecting mypy-extensions>=0.3.0 (from typing-inspect<1,>=0.4.0->dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached mypy_extensions-1.1.0-py3-none-any.whl.metadata (1.1 kB)
Collecting attrs>=22.2.0 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/attrs/attrs-25.3.0-py3-none-any.whl (63 kB)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached jsonschema_specifications-2025.4.1-py3-none-any.whl.metadata (2.9 kB)
Collecting referencing>=0.28.4 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/referencing/referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting rpds-py>=0.7.1 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.2 kB)
Using cached fastapi-0.116.1-py3-none-any.whl (95 kB)
Using cached starlette-0.47.2-py3-none-any.whl (72 kB)
Using cached uvicorn-0.35.0-py3-none-any.whl (66 kB)
Using cached supabase-2.16.0-py3-none-any.whl (17 kB)
Using cached boto3-1.39.14-py3-none-any.whl (139 kB)
Using cached opencv_python_headless-4.12.0.88-cp37-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (33.1 MB)
Using cached picamera2-0.3.30-py3-none-any.whl (121 kB)
Using cached simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (446 kB)
Using cached numpy-2.2.6-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
Using cached botocore-1.39.16-py3-none-any.whl (13.9 MB)
Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (142 kB)
Using cached gotrue-2.12.3-py3-none-any.whl (44 kB)
Using cached httpcore-1.0.9-py3-none-any.whl (78 kB)
Using cached postgrest-1.1.1-py3-none-any.whl (22 kB)
Using cached pydantic-2.11.7-py3-none-any.whl (444 kB)
Using cached pydantic_core-2.33.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
Using cached realtime-2.5.3-py3-none-any.whl (21 kB)
Using cached s3transfer-0.13.1-py3-none-any.whl (85 kB)
Using cached storage3-0.12.0-py3-none-any.whl (18 kB)
Using cached supafunc-0.10.1-py3-none-any.whl (8.0 kB)
Using cached typing_extensions-4.14.1-py3-none-any.whl (43 kB)
Using cached urllib3-2.5.0-py3-none-any.whl (129 kB)
Using cached websockets-15.0.1-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (182 kB)
Using cached certifi-2025.7.14-py3-none-any.whl (162 kB)
Using cached click-8.2.1-py3-none-any.whl (102 kB)
Using cached h11-0.16.0-py3-none-any.whl (37 kB)
Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (23 kB)
Using cached mypy_extensions-1.1.0-py3-none-any.whl (5.0 kB)
Using cached packaging-25.0-py3-none-any.whl (66 kB)
Using cached typing_inspection-0.4.1-py3-none-any.whl (14 kB)
Using cached av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl (38.2 MB)
Using cached jsonschema-4.25.0-py3-none-any.whl (89 kB)
Using cached jsonschema_specifications-2025.4.1-py3-none-any.whl (18 kB)
Using cached rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (381 kB)
Using cached libarchive_c-5.3-py3-none-any.whl (17 kB)
Using cached pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl (6.0 MB)
Using cached videodev2-0.0.4-py3-none-any.whl (49 kB)
Installing collected packages: strenum, pytz, python-prctl, libarchive-c, websockets, videodev2, urllib3, typing-extensions, tqdm, sniffio, six, rpds-py, python-multipart, python-dotenv, pyjwt, psutil, portalocker, pillow, piexif, packaging, numpy, mypy-extensions, MarkupSafe, jmespath, idna, hyperframe, hpack, h11, dnspython, click, charset-normalizer, certifi, av, attrs, annotated-types, uvicorn, typing-inspection, typing-inspect, simplejpeg, requests, referencing, realtime, python-dateutil, pydantic-core, PiDNG, opencv-python-headless, marshmallow, jinja2, httpcore, h2, email-validator, deprecation, anyio, starlette, pydantic, jsonschema-specifications, httpx, dataclasses-json, botocore, s3transfer, jsonschema, fastapi, supafunc, storage3, postgrest, picamera2, gotrue, boto3, supabase
Successfully installed MarkupSafe-3.0.2 PiDNG-4.0.9 annotated-types-0.7.0 anyio-4.9.0 attrs-25.3.0 av-15.0.0 boto3-1.39.14 botocore-1.39.16 certifi-2025.7.14 charset-normalizer-3.4.2 click-8.2.1 dataclasses-json-0.6.4 deprecation-2.1.0 dnspython-2.7.0 email-validator-2.2.0 fastapi-0.116.1 gotrue-2.12.3 h11-0.16.0 h2-4.2.0 hpack-4.1.0 httpcore-1.0.9 httpx-0.28.1 hyperframe-6.1.0 idna-3.10 jinja2-3.1.2 jmespath-1.0.1 jsonschema-4.25.0 jsonschema-specifications-2025.4.1 libarchive-c-5.3 marshmallow-3.26.1 mypy-extensions-1.1.0 numpy-2.2.6 opencv-python-headless-4.12.0.88 packaging-25.0 picamera2-0.3.30 piexif-1.1.3 pillow-11.3.0 portalocker-2.7.0 postgrest-1.1.1 psutil-5.9.5 pydantic-2.11.7 pydantic-core-2.33.2 pyjwt-2.10.1 python-dateutil-2.9.0.post0 python-dotenv-1.0.0 python-multipart-0.0.20 python-prctl-1.8.1 pytz-2025.2 realtime-2.5.3 referencing-0.36.2 requests-2.31.0 rpds-py-0.26.0 s3transfer-0.13.1 simplejpeg-1.8.2 six-1.17.0 sniffio-1.3.1 starlette-0.47.2 storage3-0.12.0 strenum-0.4.15 supabase-2.16.0 supafunc-0.10.1 tqdm-4.67.1 typing-extensions-4.14.1 typing-inspect-0.9.0 typing-inspection-0.4.1 urllib3-2.5.0 uvicorn-0.35.0 videodev2-0.0.4 websockets-15.0.1
🐍 Setting up Backend virtual environment...
📦 Creating backend virtual environment...
📦 Installing backend dependencies...
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Requirement already satisfied: pip in ./venv/lib/python3.11/site-packages (23.0.1)
Collecting pip
  Using cached pip-25.1.1-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 23.0.1
    Uninstalling pip-23.0.1:
      Successfully uninstalled pip-23.0.1
Successfully installed pip-25.1.1
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Collecting fastapi==0.116.1 (from -r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached fastapi-0.116.1-py3-none-any.whl.metadata (28 kB)
Collecting uvicorn==0.35.0 (from -r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached uvicorn-0.35.0-py3-none-any.whl.metadata (6.5 kB)
Collecting python-multipart==0.0.20 (from -r /opt/ezrec-backend/requirements.txt (line 4))
  Using cached https://www.piwheels.org/simple/python-multipart/python_multipart-0.0.20-py3-none-any.whl (24 kB)
Collecting jinja2==3.1.2 (from -r /opt/ezrec-backend/requirements.txt (line 5))
  Using cached https://www.piwheels.org/simple/jinja2/Jinja2-3.1.2-py3-none-any.whl (133 kB)
Collecting starlette==0.47.2 (from -r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached starlette-0.47.2-py3-none-any.whl.metadata (6.2 kB)
Collecting supabase==2.16.0 (from -r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached supabase-2.16.0-py3-none-any.whl.metadata (10 kB)
Collecting pyjwt<3.0.0,>=2.10.1 (from -r /opt/ezrec-backend/requirements.txt (line 10))
  Using cached https://www.piwheels.org/simple/pyjwt/PyJWT-2.10.1-py3-none-any.whl (22 kB)
Collecting boto3==1.39.14 (from -r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached boto3-1.39.14-py3-none-any.whl.metadata (6.7 kB)
Collecting psutil==5.9.5 (from -r /opt/ezrec-backend/requirements.txt (line 16))
  Using cached psutil-5.9.5-cp311-abi3-linux_aarch64.whl
Collecting python-dotenv==1.0.0 (from -r /opt/ezrec-backend/requirements.txt (line 17))
  Using cached https://www.piwheels.org/simple/python-dotenv/python_dotenv-1.0.0-py3-none-any.whl (19 kB)
Collecting requests==2.31.0 (from -r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached https://www.piwheels.org/simple/requests/requests-2.31.0-py3-none-any.whl (62 kB)
  DEPRECATION: Wheel filename 'pytz-2013d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2013d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012j-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012j-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012h-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012h-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012g-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012g-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012f-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012f-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011n-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011n-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011k-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011k-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011j-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011j-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011h-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011h-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011g-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011g-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011e-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011e-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
Collecting pytz==2025.2 (from -r /opt/ezrec-backend/requirements.txt (line 19))
  Using cached https://www.piwheels.org/simple/pytz/pytz-2025.2-py3-none-any.whl (509 kB)
Collecting email-validator==2.2.0 (from -r /opt/ezrec-backend/requirements.txt (line 22))
  Using cached https://www.piwheels.org/simple/email-validator/email_validator-2.2.0-py3-none-any.whl (33 kB)
Collecting opencv-python-headless==4.12.0.88 (from -r /opt/ezrec-backend/requirements.txt (line 25))
  Using cached opencv_python_headless-4.12.0.88-cp37-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl.metadata (19 kB)
Collecting picamera2==0.3.30 (from -r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached picamera2-0.3.30-py3-none-any.whl.metadata (6.4 kB)
Collecting simplejpeg==1.8.2 (from -r /opt/ezrec-backend/requirements.txt (line 27))
  Using cached simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (32 kB)
Collecting numpy<2.3.0,>=2.0.0 (from -r /opt/ezrec-backend/requirements.txt (line 30))
  Using cached numpy-2.2.6-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (63 kB)
Collecting python-dateutil==2.9.0.post0 (from -r /opt/ezrec-backend/requirements.txt (line 33))
  Using cached https://www.piwheels.org/simple/python-dateutil/python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
Collecting portalocker==2.7.0 (from -r /opt/ezrec-backend/requirements.txt (line 36))
  Using cached https://www.piwheels.org/simple/portalocker/portalocker-2.7.0-py2.py3-none-any.whl (15 kB)
Collecting dataclasses-json==0.6.4 (from -r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached https://archive1.piwheels.org/simple/dataclasses-json/dataclasses_json-0.6.4-py3-none-any.whl (28 kB)
Collecting pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4 (from fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached pydantic-2.11.7-py3-none-any.whl.metadata (67 kB)
Collecting typing-extensions>=4.8.0 (from fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached typing_extensions-4.14.1-py3-none-any.whl.metadata (3.0 kB)
Collecting anyio<5,>=3.6.2 (from starlette==0.47.2->-r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached https://www.piwheels.org/simple/anyio/anyio-4.9.0-py3-none-any.whl (100 kB)
Collecting click>=7.0 (from uvicorn==0.35.0->-r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached click-8.2.1-py3-none-any.whl.metadata (2.5 kB)
Collecting h11>=0.8 (from uvicorn==0.35.0->-r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting MarkupSafe>=2.0 (from jinja2==3.1.2->-r /opt/ezrec-backend/requirements.txt (line 5))
  Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.0 kB)
Collecting gotrue<3.0.0,>=2.11.0 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached gotrue-2.12.3-py3-none-any.whl.metadata (6.5 kB)
Collecting httpx<0.29,>=0.26 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/httpx/httpx-0.28.1-py3-none-any.whl (73 kB)
Collecting postgrest<1.2,>0.19 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached postgrest-1.1.1-py3-none-any.whl.metadata (3.5 kB)
Collecting realtime<2.6.0,>=2.4.0 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached realtime-2.5.3-py3-none-any.whl.metadata (6.7 kB)
Collecting storage3<0.13,>=0.10 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached storage3-0.12.0-py3-none-any.whl.metadata (1.9 kB)
Collecting supafunc<0.11,>=0.9 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached supafunc-0.10.1-py3-none-any.whl.metadata (1.2 kB)
Collecting botocore<1.40.0,>=1.39.14 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached botocore-1.39.16-py3-none-any.whl.metadata (5.7 kB)
Collecting jmespath<2.0.0,>=0.7.1 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached https://www.piwheels.org/simple/jmespath/jmespath-1.0.1-py3-none-any.whl (20 kB)
Collecting s3transfer<0.14.0,>=0.13.0 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached s3transfer-0.13.1-py3-none-any.whl.metadata (1.7 kB)
Collecting charset-normalizer<4,>=2 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (35 kB)
Collecting idna<4,>=2.5 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached https://www.piwheels.org/simple/idna/idna-3.10-py3-none-any.whl (70 kB)
Collecting urllib3<3,>=1.21.1 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached urllib3-2.5.0-py3-none-any.whl.metadata (6.5 kB)
Collecting certifi>=2017.4.17 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached certifi-2025.7.14-py3-none-any.whl.metadata (2.4 kB)
Collecting dnspython>=2.0.0 (from email-validator==2.2.0->-r /opt/ezrec-backend/requirements.txt (line 22))
  Using cached https://www.piwheels.org/simple/dnspython/dnspython-2.7.0-py3-none-any.whl (313 kB)
Collecting PiDNG (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached pidng-4.0.9-cp311-cp311-linux_aarch64.whl
Collecting av (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl.metadata (4.6 kB)
Collecting jsonschema (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached jsonschema-4.25.0-py3-none-any.whl.metadata (7.7 kB)
Collecting libarchive-c (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached libarchive_c-5.3-py3-none-any.whl.metadata (5.8 kB)
Collecting piexif (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/piexif/piexif-1.1.3-py2.py3-none-any.whl (20 kB)
Collecting pillow (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl.metadata (9.0 kB)
Collecting python-prctl (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached python_prctl-1.8.1-cp311-cp311-linux_aarch64.whl
Collecting tqdm (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/tqdm/tqdm-4.67.1-py3-none-any.whl (78 kB)
Collecting videodev2 (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached videodev2-0.0.4-py3-none-any.whl.metadata (2.8 kB)
Collecting six>=1.5 (from python-dateutil==2.9.0.post0->-r /opt/ezrec-backend/requirements.txt (line 33))
  Using cached https://www.piwheels.org/simple/six/six-1.17.0-py2.py3-none-any.whl (11 kB)
Collecting marshmallow<4.0.0,>=3.18.0 (from dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached https://www.piwheels.org/simple/marshmallow/marshmallow-3.26.1-py3-none-any.whl (50 kB)
Collecting typing-inspect<1,>=0.4.0 (from dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached https://www.piwheels.org/simple/typing-inspect/typing_inspect-0.9.0-py3-none-any.whl (8.8 kB)
Collecting sniffio>=1.1 (from anyio<5,>=3.6.2->starlette==0.47.2->-r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached https://www.piwheels.org/simple/sniffio/sniffio-1.3.1-py3-none-any.whl (10 kB)
Collecting httpcore==1.* (from httpx<0.29,>=0.26->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting h2<5,>=3 (from httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/h2/h2-4.2.0-py3-none-any.whl (60 kB)
Collecting hyperframe<7,>=6.1 (from h2<5,>=3->httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/hyperframe/hyperframe-6.1.0-py3-none-any.whl (13 kB)
Collecting hpack<5,>=4.1 (from h2<5,>=3->httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/hpack/hpack-4.1.0-py3-none-any.whl (34 kB)
Collecting packaging>=17.0 (from marshmallow<4.0.0,>=3.18.0->dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached packaging-25.0-py3-none-any.whl.metadata (3.3 kB)
Collecting deprecation<3.0.0,>=2.1.0 (from postgrest<1.2,>0.19->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/deprecation/deprecation-2.1.0-py2.py3-none-any.whl (11 kB)
Collecting annotated-types>=0.6.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached https://www.piwheels.org/simple/annotated-types/annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting pydantic-core==2.33.2 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached pydantic_core-2.33.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.8 kB)
Collecting typing-inspection>=0.4.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached typing_inspection-0.4.1-py3-none-any.whl.metadata (2.6 kB)
Collecting websockets<16,>=11 (from realtime<2.6.0,>=2.4.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached websockets-15.0.1-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.8 kB)
Collecting strenum<0.5.0,>=0.4.15 (from supafunc<0.11,>=0.9->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/strenum/StrEnum-0.4.15-py3-none-any.whl (8.9 kB)
Collecting mypy-extensions>=0.3.0 (from typing-inspect<1,>=0.4.0->dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached mypy_extensions-1.1.0-py3-none-any.whl.metadata (1.1 kB)
Collecting attrs>=22.2.0 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/attrs/attrs-25.3.0-py3-none-any.whl (63 kB)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached jsonschema_specifications-2025.4.1-py3-none-any.whl.metadata (2.9 kB)
Collecting referencing>=0.28.4 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/referencing/referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting rpds-py>=0.7.1 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.2 kB)
Using cached fastapi-0.116.1-py3-none-any.whl (95 kB)
Using cached starlette-0.47.2-py3-none-any.whl (72 kB)
Using cached uvicorn-0.35.0-py3-none-any.whl (66 kB)
Using cached supabase-2.16.0-py3-none-any.whl (17 kB)
Using cached boto3-1.39.14-py3-none-any.whl (139 kB)
Using cached opencv_python_headless-4.12.0.88-cp37-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (33.1 MB)
Using cached picamera2-0.3.30-py3-none-any.whl (121 kB)
Using cached simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (446 kB)
Using cached numpy-2.2.6-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
Using cached botocore-1.39.16-py3-none-any.whl (13.9 MB)
Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (142 kB)
Using cached gotrue-2.12.3-py3-none-any.whl (44 kB)
Using cached httpcore-1.0.9-py3-none-any.whl (78 kB)
Using cached postgrest-1.1.1-py3-none-any.whl (22 kB)
Using cached pydantic-2.11.7-py3-none-any.whl (444 kB)
Using cached pydantic_core-2.33.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
Using cached realtime-2.5.3-py3-none-any.whl (21 kB)
Using cached s3transfer-0.13.1-py3-none-any.whl (85 kB)
Using cached storage3-0.12.0-py3-none-any.whl (18 kB)
Using cached supafunc-0.10.1-py3-none-any.whl (8.0 kB)
Using cached typing_extensions-4.14.1-py3-none-any.whl (43 kB)
Using cached urllib3-2.5.0-py3-none-any.whl (129 kB)
Using cached websockets-15.0.1-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (182 kB)
Using cached certifi-2025.7.14-py3-none-any.whl (162 kB)
Using cached click-8.2.1-py3-none-any.whl (102 kB)
Using cached h11-0.16.0-py3-none-any.whl (37 kB)
Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (23 kB)
Using cached mypy_extensions-1.1.0-py3-none-any.whl (5.0 kB)
Using cached packaging-25.0-py3-none-any.whl (66 kB)
Using cached typing_inspection-0.4.1-py3-none-any.whl (14 kB)
Using cached av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl (38.2 MB)
Using cached jsonschema-4.25.0-py3-none-any.whl (89 kB)
Using cached jsonschema_specifications-2025.4.1-py3-none-any.whl (18 kB)
Using cached rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (381 kB)
Using cached libarchive_c-5.3-py3-none-any.whl (17 kB)
Using cached pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl (6.0 MB)
Using cached videodev2-0.0.4-py3-none-any.whl (49 kB)
Installing collected packages: strenum, pytz, python-prctl, libarchive-c, websockets, videodev2, urllib3, typing-extensions, tqdm, sniffio, six, rpds-py, python-multipart, python-dotenv, pyjwt, psutil, portalocker, pillow, piexif, packaging, numpy, mypy-extensions, MarkupSafe, jmespath, idna, hyperframe, hpack, h11, dnspython, click, charset-normalizer, certifi, av, attrs, annotated-types, uvicorn, typing-inspection, typing-inspect, simplejpeg, requests, referencing, realtime, python-dateutil, pydantic-core, PiDNG, opencv-python-headless, marshmallow, jinja2, httpcore, h2, email-validator, deprecation, anyio, starlette, pydantic, jsonschema-specifications, httpx, dataclasses-json, botocore, s3transfer, jsonschema, fastapi, supafunc, storage3, postgrest, picamera2, gotrue, boto3, supabase
Successfully installed MarkupSafe-3.0.2 PiDNG-4.0.9 annotated-types-0.7.0 anyio-4.9.0 attrs-25.3.0 av-15.0.0 boto3-1.39.14 botocore-1.39.16 certifi-2025.7.14 charset-normalizer-3.4.2 click-8.2.1 dataclasses-json-0.6.4 deprecation-2.1.0 dnspython-2.7.0 email-validator-2.2.0 fastapi-0.116.1 gotrue-2.12.3 h11-0.16.0 h2-4.2.0 hpack-4.1.0 httpcore-1.0.9 httpx-0.28.1 hyperframe-6.1.0 idna-3.10 jinja2-3.1.2 jmespath-1.0.1 jsonschema-4.25.0 jsonschema-specifications-2025.4.1 libarchive-c-5.3 marshmallow-3.26.1 mypy-extensions-1.1.0 numpy-2.2.6 opencv-python-headless-4.12.0.88 packaging-25.0 picamera2-0.3.30 piexif-1.1.3 pillow-11.3.0 portalocker-2.7.0 postgrest-1.1.1 psutil-5.9.5 pydantic-2.11.7 pydantic-core-2.33.2 pyjwt-2.10.1 python-dateutil-2.9.0.post0 python-dotenv-1.0.0 python-multipart-0.0.20 python-prctl-1.8.1 pytz-2025.2 realtime-2.5.3 referencing-0.36.2 requests-2.31.0 rpds-py-0.26.0 s3transfer-0.13.1 simplejpeg-1.8.2 six-1.17.0 sniffio-1.3.1 starlette-0.47.2 storage3-0.12.0 strenum-0.4.15 supabase-2.16.0 supafunc-0.10.1 tqdm-4.67.1 typing-extensions-4.14.1 typing-inspect-0.9.0 typing-inspection-0.4.1 urllib3-2.5.0 uvicorn-0.35.0 videodev2-0.0.4 websockets-15.0.1
🔐 Setting ownership for services...
🐍 Testing Python imports...
🔧 Testing other critical packages...
✅ fastapi is working
✅ supabase is working
✅ psutil is working
✅ boto3 is working
✅ Python dependencies installed successfully
⚙️ Setting up environment configuration...
📝 Creating .env file...
✅ Basic .env file created
🔧 Please edit /opt/ezrec-backend/.env with your actual credentials
🔧 Example: sudo nano /opt/ezrec-backend/.env

📋 Required environment variables:
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   USER_ID=your_user_id
   CAMERA_ID=your_camera_id
   CAMERA_0_SERIAL=your_first_camera_serial
   CAMERA_1_SERIAL=your_second_camera_serial

⚠️  The system will not work properly until these are configured!
⚙️ Installing systemd service files...
📁 Copying systemd service files...
📋 Installing dual_recorder.service...
📋 Installing ezrec-api.service...
📋 Installing system_status.service...
📋 Installing video_worker.service...
📋 Installing system_status.timer...
✅ Systemd service files installed
🔄 Reloading systemd...
🧪 Testing basic functionality...
✅ FFmpeg is available
✅ FFmpeg is working correctly
✅ FFprobe is available
✅ FFprobe is working correctly
✅ v4l2-ctl is available
📹 Camera devices:
        /dev/video20
        /dev/video21
        /dev/video22
        /dev/video23
        /dev/video24
        /dev/video25
        /dev/video26
        /dev/video27
        /dev/video28
        /dev/video29
🐍 Testing Python imports...
🔧 Testing other critical packages...
✅ fastapi is working
✅ supabase is working
✅ psutil is working
✅ boto3 is working
🎨 Creating assets...
🚀 EZREC Assets Setup
=====================
📁 Assets directory: /opt/ezrec-backend/assets
✅ Created placeholder image: /opt/ezrec-backend/assets/sponsor.png
✅ Created placeholder image: /opt/ezrec-backend/assets/company.png
✅ Created placeholder video: /opt/ezrec-backend/assets/intro.mp4

✅ Assets setup completed!
📝 Note: These are placeholder assets. Replace with actual logos and intro video.
📁 Assets location: /opt/ezrec-backend/assets
⏰ Setting up cron jobs...
✅ Log rotation cron job added
🚀 Enabling and starting services...
🔄 Resetting failed services...
🚀 Starting services...
📋 Verifying critical files...
✅ dual_recorder.py exists
✅ video_worker.py exists
✅ system_status.py exists
✅ api_server.py exists
✅ enhanced_merge.py exists
🎯 Final status check...
📊 Service Status:
● dual_recorder.service - EZREC Dual Camera Recorder Service
     Loaded: loaded (/etc/systemd/system/dual_recorder.service; enabled; preset: enabled)
     Active: active (running) since Tue 2025-07-29 21:18:09 EDT; 92ms ago
   Main PID: 11862 (python3)
      Tasks: 1 (limit: 9572)
        CPU: 72ms
     CGroup: /system.slice/dual_recorder.service
             └─11862 /opt/ezrec-backend/backend/venv/bin/python3 dual_recorder.py

Jul 29 21:18:09 raspberrypi systemd[1]: Started dual_recorder.service - EZREC Dual Camera Recorder Service.
● video_worker.service - EZREC Video Processing Worker Service
     Loaded: loaded (/etc/systemd/system/video_worker.service; enabled; preset: enabled)
     Active: active (running) since Tue 2025-07-29 21:18:09 EDT; 102ms ago
   Main PID: 11873 (python3)
      Tasks: 1 (limit: 9572)
        CPU: 82ms
     CGroup: /system.slice/video_worker.service
             └─11873 /opt/ezrec-backend/backend/venv/bin/python3 video_worker.py

Jul 29 21:18:09 raspberrypi systemd[1]: Started video_worker.service - EZREC Video Processing Worker Service.
● ezrec-api.service - EZREC FastAPI Backend
     Loaded: loaded (/etc/systemd/system/ezrec-api.service; enabled; preset: enabled)
     Active: active (running) since Tue 2025-07-29 21:18:09 EDT; 144ms ago
   Main PID: 11864 (uvicorn)
      Tasks: 1 (limit: 9572)
        CPU: 123ms
     CGroup: /system.slice/ezrec-api.service
             └─11864 /opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/api/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000

Jul 29 21:18:09 raspberrypi systemd[1]: Started ezrec-api.service - EZREC FastAPI Backend.
○ system_status.service - EZREC System Status Monitor
     Loaded: loaded (/etc/systemd/system/system_status.service; enabled; preset: enabled)
     Active: inactive (dead) since Tue 2025-07-29 21:13:33 EDT; 4min 35s ago
TriggeredBy: ● system_status.timer
   Main PID: 10675 (code=exited, status=1/FAILURE)
        CPU: 353ms

Jul 29 21:18:08 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:4: Unknown key 'Type' in section [Unit], ignoring.
Jul 29 21:18:08 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:5: Unknown key 'RemainAfterExit' in section [Unit], ignoring.
Jul 29 21:18:08 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:4: Unknown key 'Type' in section [Unit], ignoring.
Jul 29 21:18:08 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:5: Unknown key 'RemainAfterExit' in section [Unit], ignoring.
Jul 29 21:18:08 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:4: Unknown key 'Type' in section [Unit], ignoring.
Jul 29 21:18:08 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:5: Unknown key 'RemainAfterExit' in section [Unit], ignoring.
Jul 29 21:18:08 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:4: Unknown key 'Type' in section [Unit], ignoring.
Jul 29 21:18:08 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:5: Unknown key 'RemainAfterExit' in section [Unit], ignoring.
Jul 29 21:18:09 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:4: Unknown key 'Type' in section [Unit], ignoring.
Jul 29 21:18:09 raspberrypi systemd[1]: /etc/systemd/system/system_status.service:5: Unknown key 'RemainAfterExit' in section [Unit], ignoring.
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ 

michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $    chmod +x fix_venv.sh
   sudo ./fix_venv.sh
🔧 Fixing Virtual Environment Issues
====================================
🔐 Fixing ownership issues...
🧹 Removing existing virtual environments...
🐍 Creating API virtual environment...
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Requirement already satisfied: pip in ./venv/lib/python3.11/site-packages (23.0.1)
Collecting pip
  Using cached pip-25.1.1-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 23.0.1
    Uninstalling pip-23.0.1:
      Successfully uninstalled pip-23.0.1
Successfully installed pip-25.1.1
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Collecting fastapi==0.116.1 (from -r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached fastapi-0.116.1-py3-none-any.whl.metadata (28 kB)
Collecting uvicorn==0.35.0 (from -r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached uvicorn-0.35.0-py3-none-any.whl.metadata (6.5 kB)
Collecting python-multipart==0.0.20 (from -r /opt/ezrec-backend/requirements.txt (line 4))
  Using cached https://www.piwheels.org/simple/python-multipart/python_multipart-0.0.20-py3-none-any.whl (24 kB)
Collecting jinja2==3.1.2 (from -r /opt/ezrec-backend/requirements.txt (line 5))
  Downloading https://www.piwheels.org/simple/jinja2/Jinja2-3.1.2-py3-none-any.whl (133 kB)
Collecting starlette==0.47.2 (from -r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached starlette-0.47.2-py3-none-any.whl.metadata (6.2 kB)
Collecting supabase==2.16.0 (from -r /opt/ezrec-backend/requirements.txt (line 9))
  Downloading supabase-2.16.0-py3-none-any.whl.metadata (10 kB)
Collecting pyjwt<3.0.0,>=2.10.1 (from -r /opt/ezrec-backend/requirements.txt (line 10))
  Using cached https://www.piwheels.org/simple/pyjwt/PyJWT-2.10.1-py3-none-any.whl (22 kB)
Collecting boto3==1.39.14 (from -r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached boto3-1.39.14-py3-none-any.whl.metadata (6.7 kB)
Collecting psutil==5.9.5 (from -r /opt/ezrec-backend/requirements.txt (line 16))
  Downloading psutil-5.9.5.tar.gz (493 kB)
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Collecting python-dotenv==1.0.0 (from -r /opt/ezrec-backend/requirements.txt (line 17))
  Using cached https://www.piwheels.org/simple/python-dotenv/python_dotenv-1.0.0-py3-none-any.whl (19 kB)
Collecting requests==2.31.0 (from -r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached https://www.piwheels.org/simple/requests/requests-2.31.0-py3-none-any.whl (62 kB)
  DEPRECATION: Wheel filename 'pytz-2013d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2013d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012j-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012j-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012h-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012h-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012g-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012g-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012f-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012f-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011n-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011n-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011k-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011k-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011j-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011j-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011h-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011h-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011g-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011g-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011e-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011e-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
Collecting pytz==2025.2 (from -r /opt/ezrec-backend/requirements.txt (line 19))
  Downloading https://www.piwheels.org/simple/pytz/pytz-2025.2-py3-none-any.whl (509 kB)
Collecting email-validator==2.2.0 (from -r /opt/ezrec-backend/requirements.txt (line 22))
  Using cached https://www.piwheels.org/simple/email-validator/email_validator-2.2.0-py3-none-any.whl (33 kB)
Collecting opencv-python-headless==4.12.0.88 (from -r /opt/ezrec-backend/requirements.txt (line 25))
  Downloading opencv_python_headless-4.12.0.88-cp37-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl.metadata (19 kB)
Collecting picamera2==0.3.30 (from -r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading picamera2-0.3.30-py3-none-any.whl.metadata (6.4 kB)
Collecting simplejpeg==1.8.2 (from -r /opt/ezrec-backend/requirements.txt (line 27))
  Downloading simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (32 kB)
Collecting numpy<2.3.0,>=2.0.0 (from -r /opt/ezrec-backend/requirements.txt (line 30))
  Downloading numpy-2.2.6-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (63 kB)
Collecting python-dateutil==2.9.0.post0 (from -r /opt/ezrec-backend/requirements.txt (line 33))
  Using cached https://www.piwheels.org/simple/python-dateutil/python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
Collecting portalocker==2.7.0 (from -r /opt/ezrec-backend/requirements.txt (line 36))
  Downloading https://www.piwheels.org/simple/portalocker/portalocker-2.7.0-py2.py3-none-any.whl (15 kB)
Collecting dataclasses-json==0.6.4 (from -r /opt/ezrec-backend/requirements.txt (line 39))
  Downloading https://archive1.piwheels.org/simple/dataclasses-json/dataclasses_json-0.6.4-py3-none-any.whl (28 kB)
Collecting pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4 (from fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached pydantic-2.11.7-py3-none-any.whl.metadata (67 kB)
Collecting typing-extensions>=4.8.0 (from fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached typing_extensions-4.14.1-py3-none-any.whl.metadata (3.0 kB)
Collecting anyio<5,>=3.6.2 (from starlette==0.47.2->-r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached https://www.piwheels.org/simple/anyio/anyio-4.9.0-py3-none-any.whl (100 kB)
Collecting click>=7.0 (from uvicorn==0.35.0->-r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached click-8.2.1-py3-none-any.whl.metadata (2.5 kB)
Collecting h11>=0.8 (from uvicorn==0.35.0->-r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting MarkupSafe>=2.0 (from jinja2==3.1.2->-r /opt/ezrec-backend/requirements.txt (line 5))
  Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.0 kB)
Collecting gotrue<3.0.0,>=2.11.0 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached gotrue-2.12.3-py3-none-any.whl.metadata (6.5 kB)
Collecting httpx<0.29,>=0.26 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/httpx/httpx-0.28.1-py3-none-any.whl (73 kB)
Collecting postgrest<1.2,>0.19 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached postgrest-1.1.1-py3-none-any.whl.metadata (3.5 kB)
Collecting realtime<2.6.0,>=2.4.0 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Downloading realtime-2.5.3-py3-none-any.whl.metadata (6.7 kB)
Collecting storage3<0.13,>=0.10 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached storage3-0.12.0-py3-none-any.whl.metadata (1.9 kB)
Collecting supafunc<0.11,>=0.9 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached supafunc-0.10.1-py3-none-any.whl.metadata (1.2 kB)
Collecting botocore<1.40.0,>=1.39.14 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Downloading botocore-1.39.16-py3-none-any.whl.metadata (5.7 kB)
Collecting jmespath<2.0.0,>=0.7.1 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached https://www.piwheels.org/simple/jmespath/jmespath-1.0.1-py3-none-any.whl (20 kB)
Collecting s3transfer<0.14.0,>=0.13.0 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached s3transfer-0.13.1-py3-none-any.whl.metadata (1.7 kB)
Collecting charset-normalizer<4,>=2 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (35 kB)
Collecting idna<4,>=2.5 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached https://www.piwheels.org/simple/idna/idna-3.10-py3-none-any.whl (70 kB)
Collecting urllib3<3,>=1.21.1 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached urllib3-2.5.0-py3-none-any.whl.metadata (6.5 kB)
Collecting certifi>=2017.4.17 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached certifi-2025.7.14-py3-none-any.whl.metadata (2.4 kB)
Collecting dnspython>=2.0.0 (from email-validator==2.2.0->-r /opt/ezrec-backend/requirements.txt (line 22))
  Using cached https://www.piwheels.org/simple/dnspython/dnspython-2.7.0-py3-none-any.whl (313 kB)
Collecting PiDNG (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading pidng-4.0.9.tar.gz (21 kB)
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Collecting av (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl.metadata (4.6 kB)
Collecting jsonschema (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading jsonschema-4.25.0-py3-none-any.whl.metadata (7.7 kB)
Collecting libarchive-c (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading libarchive_c-5.3-py3-none-any.whl.metadata (5.8 kB)
Collecting piexif (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading https://www.piwheels.org/simple/piexif/piexif-1.1.3-py2.py3-none-any.whl (20 kB)
Collecting pillow (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl.metadata (9.0 kB)
Collecting python-prctl (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading python-prctl-1.8.1.tar.gz (28 kB)
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Collecting tqdm (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading https://www.piwheels.org/simple/tqdm/tqdm-4.67.1-py3-none-any.whl (78 kB)
Collecting videodev2 (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading videodev2-0.0.4-py3-none-any.whl.metadata (2.8 kB)
Collecting six>=1.5 (from python-dateutil==2.9.0.post0->-r /opt/ezrec-backend/requirements.txt (line 33))
  Using cached https://www.piwheels.org/simple/six/six-1.17.0-py2.py3-none-any.whl (11 kB)
Collecting marshmallow<4.0.0,>=3.18.0 (from dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Downloading https://www.piwheels.org/simple/marshmallow/marshmallow-3.26.1-py3-none-any.whl (50 kB)
Collecting typing-inspect<1,>=0.4.0 (from dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Downloading https://www.piwheels.org/simple/typing-inspect/typing_inspect-0.9.0-py3-none-any.whl (8.8 kB)
Collecting sniffio>=1.1 (from anyio<5,>=3.6.2->starlette==0.47.2->-r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached https://www.piwheels.org/simple/sniffio/sniffio-1.3.1-py3-none-any.whl (10 kB)
Collecting httpcore==1.* (from httpx<0.29,>=0.26->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting h2<5,>=3 (from httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/h2/h2-4.2.0-py3-none-any.whl (60 kB)
Collecting hyperframe<7,>=6.1 (from h2<5,>=3->httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/hyperframe/hyperframe-6.1.0-py3-none-any.whl (13 kB)
Collecting hpack<5,>=4.1 (from h2<5,>=3->httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/hpack/hpack-4.1.0-py3-none-any.whl (34 kB)
Collecting packaging>=17.0 (from marshmallow<4.0.0,>=3.18.0->dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached packaging-25.0-py3-none-any.whl.metadata (3.3 kB)
Collecting deprecation<3.0.0,>=2.1.0 (from postgrest<1.2,>0.19->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/deprecation/deprecation-2.1.0-py2.py3-none-any.whl (11 kB)
Collecting annotated-types>=0.6.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached https://www.piwheels.org/simple/annotated-types/annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting pydantic-core==2.33.2 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached pydantic_core-2.33.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.8 kB)
Collecting typing-inspection>=0.4.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached typing_inspection-0.4.1-py3-none-any.whl.metadata (2.6 kB)
Collecting websockets<16,>=11 (from realtime<2.6.0,>=2.4.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached websockets-15.0.1-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.8 kB)
Collecting strenum<0.5.0,>=0.4.15 (from supafunc<0.11,>=0.9->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/strenum/StrEnum-0.4.15-py3-none-any.whl (8.9 kB)
Collecting mypy-extensions>=0.3.0 (from typing-inspect<1,>=0.4.0->dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Downloading mypy_extensions-1.1.0-py3-none-any.whl.metadata (1.1 kB)
Collecting attrs>=22.2.0 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading https://www.piwheels.org/simple/attrs/attrs-25.3.0-py3-none-any.whl (63 kB)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading jsonschema_specifications-2025.4.1-py3-none-any.whl.metadata (2.9 kB)
Collecting referencing>=0.28.4 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading https://www.piwheels.org/simple/referencing/referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting rpds-py>=0.7.1 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Downloading rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.2 kB)
Using cached fastapi-0.116.1-py3-none-any.whl (95 kB)
Using cached starlette-0.47.2-py3-none-any.whl (72 kB)
Using cached uvicorn-0.35.0-py3-none-any.whl (66 kB)
Downloading supabase-2.16.0-py3-none-any.whl (17 kB)
Using cached boto3-1.39.14-py3-none-any.whl (139 kB)
Downloading opencv_python_headless-4.12.0.88-cp37-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (33.1 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 33.1/33.1 MB 3.9 MB/s eta 0:00:00
Downloading picamera2-0.3.30-py3-none-any.whl (121 kB)
Downloading simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (446 kB)
Downloading numpy-2.2.6-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.3/14.3 MB 3.9 MB/s eta 0:00:00
Downloading botocore-1.39.16-py3-none-any.whl (13.9 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.9/13.9 MB 3.8 MB/s eta 0:00:00
Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (142 kB)
Using cached gotrue-2.12.3-py3-none-any.whl (44 kB)
Using cached httpcore-1.0.9-py3-none-any.whl (78 kB)
Using cached postgrest-1.1.1-py3-none-any.whl (22 kB)
Using cached pydantic-2.11.7-py3-none-any.whl (444 kB)
Using cached pydantic_core-2.33.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
Downloading realtime-2.5.3-py3-none-any.whl (21 kB)
Using cached s3transfer-0.13.1-py3-none-any.whl (85 kB)
Using cached storage3-0.12.0-py3-none-any.whl (18 kB)
Using cached supafunc-0.10.1-py3-none-any.whl (8.0 kB)
Using cached typing_extensions-4.14.1-py3-none-any.whl (43 kB)
Using cached urllib3-2.5.0-py3-none-any.whl (129 kB)
Using cached websockets-15.0.1-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (182 kB)
Using cached certifi-2025.7.14-py3-none-any.whl (162 kB)
Using cached click-8.2.1-py3-none-any.whl (102 kB)
Using cached h11-0.16.0-py3-none-any.whl (37 kB)
Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (23 kB)
Downloading mypy_extensions-1.1.0-py3-none-any.whl (5.0 kB)
Using cached packaging-25.0-py3-none-any.whl (66 kB)
Using cached typing_inspection-0.4.1-py3-none-any.whl (14 kB)
Downloading av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl (38.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 38.2/38.2 MB 4.0 MB/s eta 0:00:00
Downloading jsonschema-4.25.0-py3-none-any.whl (89 kB)
Downloading jsonschema_specifications-2025.4.1-py3-none-any.whl (18 kB)
Downloading rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (381 kB)
Downloading libarchive_c-5.3-py3-none-any.whl (17 kB)
Downloading pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl (6.0 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 6.0/6.0 MB 3.3 MB/s eta 0:00:00
Downloading videodev2-0.0.4-py3-none-any.whl (49 kB)
Building wheels for collected packages: psutil, PiDNG, python-prctl
  Building wheel for psutil (pyproject.toml) ... done
  Created wheel for psutil: filename=psutil-5.9.5-cp311-abi3-linux_aarch64.whl size=279456 sha256=c36414d43127fae1a95059379536c1ee727a6c5f38b7f1c48fae3788916cc344
  Stored in directory: /root/.cache/pip/wheels/1c/69/e2/589eceb30be31a7e846a5b4ae528b0cf70c56d7e287e4ffb81
  Building wheel for PiDNG (pyproject.toml) ... done
  Created wheel for PiDNG: filename=pidng-4.0.9-cp311-cp311-linux_aarch64.whl size=54260 sha256=5a89bc7c289c5ddcccfcd053723c87cd1ec6acc77f51b8c47d5e42bcf3fdd162
  Stored in directory: /root/.cache/pip/wheels/9e/b0/1b/95c32fd1faba57abb0f69b2eba2bb9821095dfdfb2b8feace5
  Building wheel for python-prctl (pyproject.toml) ... done
  Created wheel for python-prctl: filename=python_prctl-1.8.1-cp311-cp311-linux_aarch64.whl size=26218 sha256=ef3e6a7157e3d98420ee670d03bcfb54116c49e1699055dde9a4a49f28218e32
  Stored in directory: /root/.cache/pip/wheels/5d/66/87/0ece41453258a935c273d5b727a0a2982a82e9d205287446d7
Successfully built psutil PiDNG python-prctl
Installing collected packages: strenum, pytz, python-prctl, libarchive-c, websockets, videodev2, urllib3, typing-extensions, tqdm, sniffio, six, rpds-py, python-multipart, python-dotenv, pyjwt, psutil, portalocker, pillow, piexif, packaging, numpy, mypy-extensions, MarkupSafe, jmespath, idna, hyperframe, hpack, h11, dnspython, click, charset-normalizer, certifi, av, attrs, annotated-types, uvicorn, typing-inspection, typing-inspect, simplejpeg, requests, referencing, realtime, python-dateutil, pydantic-core, PiDNG, opencv-python-headless, marshmallow, jinja2, httpcore, h2, email-validator, deprecation, anyio, starlette, pydantic, jsonschema-specifications, httpx, dataclasses-json, botocore, s3transfer, jsonschema, fastapi, supafunc, storage3, postgrest, picamera2, gotrue, boto3, supabase
Successfully installed MarkupSafe-3.0.2 PiDNG-4.0.9 annotated-types-0.7.0 anyio-4.9.0 attrs-25.3.0 av-15.0.0 boto3-1.39.14 botocore-1.39.16 certifi-2025.7.14 charset-normalizer-3.4.2 click-8.2.1 dataclasses-json-0.6.4 deprecation-2.1.0 dnspython-2.7.0 email-validator-2.2.0 fastapi-0.116.1 gotrue-2.12.3 h11-0.16.0 h2-4.2.0 hpack-4.1.0 httpcore-1.0.9 httpx-0.28.1 hyperframe-6.1.0 idna-3.10 jinja2-3.1.2 jmespath-1.0.1 jsonschema-4.25.0 jsonschema-specifications-2025.4.1 libarchive-c-5.3 marshmallow-3.26.1 mypy-extensions-1.1.0 numpy-2.2.6 opencv-python-headless-4.12.0.88 packaging-25.0 picamera2-0.3.30 piexif-1.1.3 pillow-11.3.0 portalocker-2.7.0 postgrest-1.1.1 psutil-5.9.5 pydantic-2.11.7 pydantic-core-2.33.2 pyjwt-2.10.1 python-dateutil-2.9.0.post0 python-dotenv-1.0.0 python-multipart-0.0.20 python-prctl-1.8.1 pytz-2025.2 realtime-2.5.3 referencing-0.36.2 requests-2.31.0 rpds-py-0.26.0 s3transfer-0.13.1 simplejpeg-1.8.2 six-1.17.0 sniffio-1.3.1 starlette-0.47.2 storage3-0.12.0 strenum-0.4.15 supabase-2.16.0 supafunc-0.10.1 tqdm-4.67.1 typing-extensions-4.14.1 typing-inspect-0.9.0 typing-inspection-0.4.1 urllib3-2.5.0 uvicorn-0.35.0 videodev2-0.0.4 websockets-15.0.1
🐍 Creating backend virtual environment...
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Requirement already satisfied: pip in ./venv/lib/python3.11/site-packages (23.0.1)
Collecting pip
  Using cached pip-25.1.1-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 23.0.1
    Uninstalling pip-23.0.1:
      Successfully uninstalled pip-23.0.1
Successfully installed pip-25.1.1
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Collecting fastapi==0.116.1 (from -r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached fastapi-0.116.1-py3-none-any.whl.metadata (28 kB)
Collecting uvicorn==0.35.0 (from -r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached uvicorn-0.35.0-py3-none-any.whl.metadata (6.5 kB)
Collecting python-multipart==0.0.20 (from -r /opt/ezrec-backend/requirements.txt (line 4))
  Using cached https://www.piwheels.org/simple/python-multipart/python_multipart-0.0.20-py3-none-any.whl (24 kB)
Collecting jinja2==3.1.2 (from -r /opt/ezrec-backend/requirements.txt (line 5))
  Using cached https://www.piwheels.org/simple/jinja2/Jinja2-3.1.2-py3-none-any.whl (133 kB)
Collecting starlette==0.47.2 (from -r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached starlette-0.47.2-py3-none-any.whl.metadata (6.2 kB)
Collecting supabase==2.16.0 (from -r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached supabase-2.16.0-py3-none-any.whl.metadata (10 kB)
Collecting pyjwt<3.0.0,>=2.10.1 (from -r /opt/ezrec-backend/requirements.txt (line 10))
  Using cached https://www.piwheels.org/simple/pyjwt/PyJWT-2.10.1-py3-none-any.whl (22 kB)
Collecting boto3==1.39.14 (from -r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached boto3-1.39.14-py3-none-any.whl.metadata (6.7 kB)
Collecting psutil==5.9.5 (from -r /opt/ezrec-backend/requirements.txt (line 16))
  Using cached psutil-5.9.5-cp311-abi3-linux_aarch64.whl
Collecting python-dotenv==1.0.0 (from -r /opt/ezrec-backend/requirements.txt (line 17))
  Using cached https://www.piwheels.org/simple/python-dotenv/python_dotenv-1.0.0-py3-none-any.whl (19 kB)
Collecting requests==2.31.0 (from -r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached https://www.piwheels.org/simple/requests/requests-2.31.0-py3-none-any.whl (62 kB)
  DEPRECATION: Wheel filename 'pytz-2013d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2013d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012j-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012j-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012h-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012h-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012g-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012g-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012f-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012f-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2012d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2012d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011n-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011n-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011k-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011k-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011j-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011j-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011h-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011h-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011g-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011g-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011e-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011e-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
  DEPRECATION: Wheel filename 'pytz-2011d-py3-none-any.whl' is not correctly normalised. Future versions of pip will raise the following error:
  Invalid wheel filename (invalid version): 'pytz-2011d-py3-none-any'
  
   pip 25.3 will enforce this behaviour change. A possible replacement is to rename the wheel to use a correctly normalised name (this may require updating the version in the project metadata). Discussion can be found at https://github.com/pypa/pip/issues/12938
Collecting pytz==2025.2 (from -r /opt/ezrec-backend/requirements.txt (line 19))
  Using cached https://www.piwheels.org/simple/pytz/pytz-2025.2-py3-none-any.whl (509 kB)
Collecting email-validator==2.2.0 (from -r /opt/ezrec-backend/requirements.txt (line 22))
  Using cached https://www.piwheels.org/simple/email-validator/email_validator-2.2.0-py3-none-any.whl (33 kB)
Collecting opencv-python-headless==4.12.0.88 (from -r /opt/ezrec-backend/requirements.txt (line 25))
  Using cached opencv_python_headless-4.12.0.88-cp37-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl.metadata (19 kB)
Collecting picamera2==0.3.30 (from -r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached picamera2-0.3.30-py3-none-any.whl.metadata (6.4 kB)
Collecting simplejpeg==1.8.2 (from -r /opt/ezrec-backend/requirements.txt (line 27))
  Using cached simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (32 kB)
Collecting numpy<2.3.0,>=2.0.0 (from -r /opt/ezrec-backend/requirements.txt (line 30))
  Using cached numpy-2.2.6-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (63 kB)
Collecting python-dateutil==2.9.0.post0 (from -r /opt/ezrec-backend/requirements.txt (line 33))
  Using cached https://www.piwheels.org/simple/python-dateutil/python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
Collecting portalocker==2.7.0 (from -r /opt/ezrec-backend/requirements.txt (line 36))
  Using cached https://www.piwheels.org/simple/portalocker/portalocker-2.7.0-py2.py3-none-any.whl (15 kB)
Collecting dataclasses-json==0.6.4 (from -r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached https://archive1.piwheels.org/simple/dataclasses-json/dataclasses_json-0.6.4-py3-none-any.whl (28 kB)
Collecting pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4 (from fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached pydantic-2.11.7-py3-none-any.whl.metadata (67 kB)
Collecting typing-extensions>=4.8.0 (from fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached typing_extensions-4.14.1-py3-none-any.whl.metadata (3.0 kB)
Collecting anyio<5,>=3.6.2 (from starlette==0.47.2->-r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached https://www.piwheels.org/simple/anyio/anyio-4.9.0-py3-none-any.whl (100 kB)
Collecting click>=7.0 (from uvicorn==0.35.0->-r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached click-8.2.1-py3-none-any.whl.metadata (2.5 kB)
Collecting h11>=0.8 (from uvicorn==0.35.0->-r /opt/ezrec-backend/requirements.txt (line 3))
  Using cached h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting MarkupSafe>=2.0 (from jinja2==3.1.2->-r /opt/ezrec-backend/requirements.txt (line 5))
  Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.0 kB)
Collecting gotrue<3.0.0,>=2.11.0 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached gotrue-2.12.3-py3-none-any.whl.metadata (6.5 kB)
Collecting httpx<0.29,>=0.26 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/httpx/httpx-0.28.1-py3-none-any.whl (73 kB)
Collecting postgrest<1.2,>0.19 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached postgrest-1.1.1-py3-none-any.whl.metadata (3.5 kB)
Collecting realtime<2.6.0,>=2.4.0 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached realtime-2.5.3-py3-none-any.whl.metadata (6.7 kB)
Collecting storage3<0.13,>=0.10 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached storage3-0.12.0-py3-none-any.whl.metadata (1.9 kB)
Collecting supafunc<0.11,>=0.9 (from supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached supafunc-0.10.1-py3-none-any.whl.metadata (1.2 kB)
Collecting botocore<1.40.0,>=1.39.14 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached botocore-1.39.16-py3-none-any.whl.metadata (5.7 kB)
Collecting jmespath<2.0.0,>=0.7.1 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached https://www.piwheels.org/simple/jmespath/jmespath-1.0.1-py3-none-any.whl (20 kB)
Collecting s3transfer<0.14.0,>=0.13.0 (from boto3==1.39.14->-r /opt/ezrec-backend/requirements.txt (line 13))
  Using cached s3transfer-0.13.1-py3-none-any.whl.metadata (1.7 kB)
Collecting charset-normalizer<4,>=2 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (35 kB)
Collecting idna<4,>=2.5 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached https://www.piwheels.org/simple/idna/idna-3.10-py3-none-any.whl (70 kB)
Collecting urllib3<3,>=1.21.1 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached urllib3-2.5.0-py3-none-any.whl.metadata (6.5 kB)
Collecting certifi>=2017.4.17 (from requests==2.31.0->-r /opt/ezrec-backend/requirements.txt (line 18))
  Using cached certifi-2025.7.14-py3-none-any.whl.metadata (2.4 kB)
Collecting dnspython>=2.0.0 (from email-validator==2.2.0->-r /opt/ezrec-backend/requirements.txt (line 22))
  Using cached https://www.piwheels.org/simple/dnspython/dnspython-2.7.0-py3-none-any.whl (313 kB)
Collecting PiDNG (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached pidng-4.0.9-cp311-cp311-linux_aarch64.whl
Collecting av (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl.metadata (4.6 kB)
Collecting jsonschema (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached jsonschema-4.25.0-py3-none-any.whl.metadata (7.7 kB)
Collecting libarchive-c (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached libarchive_c-5.3-py3-none-any.whl.metadata (5.8 kB)
Collecting piexif (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/piexif/piexif-1.1.3-py2.py3-none-any.whl (20 kB)
Collecting pillow (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl.metadata (9.0 kB)
Collecting python-prctl (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached python_prctl-1.8.1-cp311-cp311-linux_aarch64.whl
Collecting tqdm (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/tqdm/tqdm-4.67.1-py3-none-any.whl (78 kB)
Collecting videodev2 (from picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached videodev2-0.0.4-py3-none-any.whl.metadata (2.8 kB)
Collecting six>=1.5 (from python-dateutil==2.9.0.post0->-r /opt/ezrec-backend/requirements.txt (line 33))
  Using cached https://www.piwheels.org/simple/six/six-1.17.0-py2.py3-none-any.whl (11 kB)
Collecting marshmallow<4.0.0,>=3.18.0 (from dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached https://www.piwheels.org/simple/marshmallow/marshmallow-3.26.1-py3-none-any.whl (50 kB)
Collecting typing-inspect<1,>=0.4.0 (from dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached https://www.piwheels.org/simple/typing-inspect/typing_inspect-0.9.0-py3-none-any.whl (8.8 kB)
Collecting sniffio>=1.1 (from anyio<5,>=3.6.2->starlette==0.47.2->-r /opt/ezrec-backend/requirements.txt (line 6))
  Using cached https://www.piwheels.org/simple/sniffio/sniffio-1.3.1-py3-none-any.whl (10 kB)
Collecting httpcore==1.* (from httpx<0.29,>=0.26->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting h2<5,>=3 (from httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/h2/h2-4.2.0-py3-none-any.whl (60 kB)
Collecting hyperframe<7,>=6.1 (from h2<5,>=3->httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/hyperframe/hyperframe-6.1.0-py3-none-any.whl (13 kB)
Collecting hpack<5,>=4.1 (from h2<5,>=3->httpx[http2]<0.29,>=0.26->gotrue<3.0.0,>=2.11.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/hpack/hpack-4.1.0-py3-none-any.whl (34 kB)
Collecting packaging>=17.0 (from marshmallow<4.0.0,>=3.18.0->dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached packaging-25.0-py3-none-any.whl.metadata (3.3 kB)
Collecting deprecation<3.0.0,>=2.1.0 (from postgrest<1.2,>0.19->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/deprecation/deprecation-2.1.0-py2.py3-none-any.whl (11 kB)
Collecting annotated-types>=0.6.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached https://www.piwheels.org/simple/annotated-types/annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting pydantic-core==2.33.2 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached pydantic_core-2.33.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.8 kB)
Collecting typing-inspection>=0.4.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.116.1->-r /opt/ezrec-backend/requirements.txt (line 2))
  Using cached typing_inspection-0.4.1-py3-none-any.whl.metadata (2.6 kB)
Collecting websockets<16,>=11 (from realtime<2.6.0,>=2.4.0->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached websockets-15.0.1-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.8 kB)
Collecting strenum<0.5.0,>=0.4.15 (from supafunc<0.11,>=0.9->supabase==2.16.0->-r /opt/ezrec-backend/requirements.txt (line 9))
  Using cached https://www.piwheels.org/simple/strenum/StrEnum-0.4.15-py3-none-any.whl (8.9 kB)
Collecting mypy-extensions>=0.3.0 (from typing-inspect<1,>=0.4.0->dataclasses-json==0.6.4->-r /opt/ezrec-backend/requirements.txt (line 39))
  Using cached mypy_extensions-1.1.0-py3-none-any.whl.metadata (1.1 kB)
Collecting attrs>=22.2.0 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/attrs/attrs-25.3.0-py3-none-any.whl (63 kB)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached jsonschema_specifications-2025.4.1-py3-none-any.whl.metadata (2.9 kB)
Collecting referencing>=0.28.4 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached https://www.piwheels.org/simple/referencing/referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting rpds-py>=0.7.1 (from jsonschema->picamera2==0.3.30->-r /opt/ezrec-backend/requirements.txt (line 26))
  Using cached rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.2 kB)
Using cached fastapi-0.116.1-py3-none-any.whl (95 kB)
Using cached starlette-0.47.2-py3-none-any.whl (72 kB)
Using cached uvicorn-0.35.0-py3-none-any.whl (66 kB)
Using cached supabase-2.16.0-py3-none-any.whl (17 kB)
Using cached boto3-1.39.14-py3-none-any.whl (139 kB)
Using cached opencv_python_headless-4.12.0.88-cp37-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (33.1 MB)
Using cached picamera2-0.3.30-py3-none-any.whl (121 kB)
Using cached simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (446 kB)
Using cached numpy-2.2.6-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
Using cached botocore-1.39.16-py3-none-any.whl (13.9 MB)
Using cached charset_normalizer-3.4.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (142 kB)
Using cached gotrue-2.12.3-py3-none-any.whl (44 kB)
Using cached httpcore-1.0.9-py3-none-any.whl (78 kB)
Using cached postgrest-1.1.1-py3-none-any.whl (22 kB)
Using cached pydantic-2.11.7-py3-none-any.whl (444 kB)
Using cached pydantic_core-2.33.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
Using cached realtime-2.5.3-py3-none-any.whl (21 kB)
Using cached s3transfer-0.13.1-py3-none-any.whl (85 kB)
Using cached storage3-0.12.0-py3-none-any.whl (18 kB)
Using cached supafunc-0.10.1-py3-none-any.whl (8.0 kB)
Using cached typing_extensions-4.14.1-py3-none-any.whl (43 kB)
Using cached urllib3-2.5.0-py3-none-any.whl (129 kB)
Using cached websockets-15.0.1-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (182 kB)
Using cached certifi-2025.7.14-py3-none-any.whl (162 kB)
Using cached click-8.2.1-py3-none-any.whl (102 kB)
Using cached h11-0.16.0-py3-none-any.whl (37 kB)
Using cached MarkupSafe-3.0.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (23 kB)
Using cached mypy_extensions-1.1.0-py3-none-any.whl (5.0 kB)
Using cached packaging-25.0-py3-none-any.whl (66 kB)
Using cached typing_inspection-0.4.1-py3-none-any.whl (14 kB)
Using cached av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl (38.2 MB)
Using cached jsonschema-4.25.0-py3-none-any.whl (89 kB)
Using cached jsonschema_specifications-2025.4.1-py3-none-any.whl (18 kB)
Using cached rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (381 kB)
Using cached libarchive_c-5.3-py3-none-any.whl (17 kB)
Using cached pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl (6.0 MB)
Using cached videodev2-0.0.4-py3-none-any.whl (49 kB)
Installing collected packages: strenum, pytz, python-prctl, libarchive-c, websockets, videodev2, urllib3, typing-extensions, tqdm, sniffio, six, rpds-py, python-multipart, python-dotenv, pyjwt, psutil, portalocker, pillow, piexif, packaging, numpy, mypy-extensions, MarkupSafe, jmespath, idna, hyperframe, hpack, h11, dnspython, click, charset-normalizer, certifi, av, attrs, annotated-types, uvicorn, typing-inspection, typing-inspect, simplejpeg, requests, referencing, realtime, python-dateutil, pydantic-core, PiDNG, opencv-python-headless, marshmallow, jinja2, httpcore, h2, email-validator, deprecation, anyio, starlette, pydantic, jsonschema-specifications, httpx, dataclasses-json, botocore, s3transfer, jsonschema, fastapi, supafunc, storage3, postgrest, picamera2, gotrue, boto3, supabase
Successfully installed MarkupSafe-3.0.2 PiDNG-4.0.9 annotated-types-0.7.0 anyio-4.9.0 attrs-25.3.0 av-15.0.0 boto3-1.39.14 botocore-1.39.16 certifi-2025.7.14 charset-normalizer-3.4.2 click-8.2.1 dataclasses-json-0.6.4 deprecation-2.1.0 dnspython-2.7.0 email-validator-2.2.0 fastapi-0.116.1 gotrue-2.12.3 h11-0.16.0 h2-4.2.0 hpack-4.1.0 httpcore-1.0.9 httpx-0.28.1 hyperframe-6.1.0 idna-3.10 jinja2-3.1.2 jmespath-1.0.1 jsonschema-4.25.0 jsonschema-specifications-2025.4.1 libarchive-c-5.3 marshmallow-3.26.1 mypy-extensions-1.1.0 numpy-2.2.6 opencv-python-headless-4.12.0.88 packaging-25.0 picamera2-0.3.30 piexif-1.1.3 pillow-11.3.0 portalocker-2.7.0 postgrest-1.1.1 psutil-5.9.5 pydantic-2.11.7 pydantic-core-2.33.2 pyjwt-2.10.1 python-dateutil-2.9.0.post0 python-dotenv-1.0.0 python-multipart-0.0.20 python-prctl-1.8.1 pytz-2025.2 realtime-2.5.3 referencing-0.36.2 requests-2.31.0 rpds-py-0.26.0 s3transfer-0.13.1 simplejpeg-1.8.2 six-1.17.0 sniffio-1.3.1 starlette-0.47.2 storage3-0.12.0 strenum-0.4.15 supabase-2.16.0 supafunc-0.10.1 tqdm-4.67.1 typing-extensions-4.14.1 typing-inspect-0.9.0 typing-inspection-0.4.1 urllib3-2.5.0 uvicorn-0.35.0 videodev2-0.0.4 websockets-15.0.1
🔐 Setting ownership for services...
🎨 Creating assets...
🚀 EZREC Assets Setup
=====================
📁 Assets directory: /opt/ezrec-backend/assets
⏭️ Asset already exists: sponsor.png
⏭️ Asset already exists: company.png
⏭️ Asset already exists: intro.mp4

✅ Assets setup completed!
📝 Note: These are placeholder assets. Replace with actual logos and intro video.
📁 Assets location: /opt/ezrec-backend/assets
🔄 Restarting services...
📊 Checking service status...
● dual_recorder.service - EZREC Dual Camera Recorder Service
     Loaded: loaded (/etc/systemd/system/dual_recorder.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Tue 2025-07-29 21:20:46 EDT; 2s ago
    Process: 12476 ExecStart=/opt/ezrec-backend/backend/venv/bin/python3 dual_recorder.py (code=exited, status=1/FAILURE)
   Main PID: 12476 (code=exited, status=1/FAILURE)
        CPU: 467ms
● video_worker.service - EZREC Video Processing Worker Service
     Loaded: loaded (/etc/systemd/system/video_worker.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Tue 2025-07-29 21:20:46 EDT; 2s ago
    Process: 12481 ExecStart=/opt/ezrec-backend/backend/venv/bin/python3 video_worker.py (code=exited, status=1/FAILURE)
   Main PID: 12481 (code=exited, status=1/FAILURE)
        CPU: 625ms
● ezrec-api.service - EZREC FastAPI Backend
     Loaded: loaded (/etc/systemd/system/ezrec-api.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Tue 2025-07-29 21:20:46 EDT; 2s ago
    Process: 12486 ExecStart=/opt/ezrec-backend/api/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000 (code=exited, status=1/FAILURE)
   Main PID: 12486 (code=exited, status=1/FAILURE)
        CPU: 1.267s

Jul 29 21:20:46 raspberrypi systemd[1]: ezrec-api.service: Consumed 1.267s CPU time.
✅ Virtual environment fix completed!
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ 
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $    python3 test_complete_system.py
🚀 EZREC Complete System Test
==============================


🧪 Testing System Requirements...
🔧 Testing System Requirements...
✅ Python version: 3.11.2 (main, Apr 28 2025, 14:11:48) [GCC 12.2.0]
✅ FFmpeg is available
✅ v4l2-ctl is available


🧪 Testing Virtual Environments...

🐍 Testing Virtual Environments...
✅ API virtual environment exists
✅ API venv imports successful
✅ Backend virtual environment exists
❌ Backend venv imports failed: Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/picamera2/__init__.py", line 4, in <module>
    import libcamera
ModuleNotFoundError: No module named 'libcamera'

❌ Virtual Environments test failed


🧪 Testing Services...

🚀 Testing Services...
❌ dual_recorder.service: activating
❌ Services test failed


🧪 Testing API Endpoints...

🌐 Testing API Endpoints...
⏳ Waiting for API to start...
❌ API server not running (Connection refused)
❌ API Endpoints test failed


🧪 Testing Directories...

📁 Testing Directories...
✅ /opt/ezrec-backend/recordings
✅ /opt/ezrec-backend/processed
✅ /opt/ezrec-backend/final
✅ /opt/ezrec-backend/assets
✅ /opt/ezrec-backend/logs
✅ /opt/ezrec-backend/events
✅ /opt/ezrec-backend/api/local_data


🧪 Testing Assets...

🎨 Testing Assets...
✅ /opt/ezrec-backend/assets/sponsor.png
✅ /opt/ezrec-backend/assets/company.png
✅ /opt/ezrec-backend/assets/intro.mp4


🧪 Testing Camera Detection...

📹 Testing Camera Detection...
✅ Camera devices detected
   Found 33 video device(s)


🧪 Testing Booking Creation...

📝 Testing Booking Creation...
❌ Booking creation error: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url: /bookings (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7fff9f0da390>: Failed to establish a new connection: [Errno 111] Connection refused'))
❌ Booking Creation test failed

📊 Complete Test Results:
✅ Passed: 4/8
❌ Failed: 4/8

⚠️ Some tests failed. Check the output above for issues.

🔧 Troubleshooting:
1. Run: sudo ./fix_venv.sh
2. Check service logs: sudo journalctl -u ezrec-api.service -f
3. Restart services: sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ 
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ # Quick API test
python3 test_api_quick.py

# Complete system test
python3 test_complete_system.py

# Check service status
sudo systemctl status dual_recorder.service video_worker.service ezrec-api.service

# View logs
sudo journalctl -u ezrec-api.service -f
🚀 EZREC Quick API Test
=======================

🔍 Checking service status...
❌ dual_recorder.service: activating
❌ video_worker.service: activating
❌ ezrec-api.service: activating

⏳ Waiting 10 seconds for services to start...

🧪 Testing API Status...
🧪 Testing API status...
❌ API server not running (Connection refused)


🧪 Testing Booking Creation...
🧪 Testing booking creation...
❌ Booking creation error: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url: /bookings (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7fff72e24a10>: Failed to establish a new connection: [Errno 111] Connection refused'))

📊 Quick Test Results:
✅ Passed: 0/2
❌ Failed: 2/2
⚠️ Some tests failed

🔧 Troubleshooting:
1. Check service status: sudo systemctl status ezrec-api.service
2. Check logs: sudo journalctl -u ezrec-api.service -f
3. Restart API: sudo systemctl restart ezrec-api.service
🚀 EZREC Complete System Test
==============================


🧪 Testing System Requirements...
🔧 Testing System Requirements...
✅ Python version: 3.11.2 (main, Apr 28 2025, 14:11:48) [GCC 12.2.0]
✅ FFmpeg is available
✅ v4l2-ctl is available


🧪 Testing Virtual Environments...

🐍 Testing Virtual Environments...
✅ API virtual environment exists
✅ API venv imports successful
✅ Backend virtual environment exists
❌ Backend venv imports failed: Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/picamera2/__init__.py", line 4, in <module>
    import libcamera
ModuleNotFoundError: No module named 'libcamera'

❌ Virtual Environments test failed


🧪 Testing Services...

🚀 Testing Services...
❌ dual_recorder.service: activating
❌ Services test failed


🧪 Testing API Endpoints...

🌐 Testing API Endpoints...
⏳ Waiting for API to start...
❌ API server not running (Connection refused)
❌ API Endpoints test failed


🧪 Testing Directories...

📁 Testing Directories...
✅ /opt/ezrec-backend/recordings
✅ /opt/ezrec-backend/processed
✅ /opt/ezrec-backend/final
✅ /opt/ezrec-backend/assets
✅ /opt/ezrec-backend/logs
✅ /opt/ezrec-backend/events
✅ /opt/ezrec-backend/api/local_data


🧪 Testing Assets...

🎨 Testing Assets...
✅ /opt/ezrec-backend/assets/sponsor.png
✅ /opt/ezrec-backend/assets/company.png
✅ /opt/ezrec-backend/assets/intro.mp4


🧪 Testing Camera Detection...

📹 Testing Camera Detection...
✅ Camera devices detected
   Found 33 video device(s)


🧪 Testing Booking Creation...

📝 Testing Booking Creation...
❌ Booking creation error: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url: /bookings (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7fff957ea390>: Failed to establish a new connection: [Errno 111] Connection refused'))
❌ Booking Creation test failed

📊 Complete Test Results:
✅ Passed: 4/8
❌ Failed: 4/8

⚠️ Some tests failed. Check the output above for issues.

🔧 Troubleshooting:
1. Run: sudo ./fix_venv.sh
2. Check service logs: sudo journalctl -u ezrec-api.service -f
3. Restart services: sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service
● dual_recorder.service - EZREC Dual Camera Recorder Service
     Loaded: loaded (/etc/systemd/system/dual_recorder.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Tue 2025-07-29 21:22:10 EDT; 2s ago
    Process: 12685 ExecStart=/opt/ezrec-backend/backend/venv/bin/python3 dual_recorder.py (code=exited, status=1/FAILURE)
   Main PID: 12685 (code=exited, status=1/FAILURE)
        CPU: 383ms

● video_worker.service - EZREC Video Processing Worker Service
     Loaded: loaded (/etc/systemd/system/video_worker.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Tue 2025-07-29 21:22:12 EDT; 402ms ago
    Process: 12688 ExecStart=/opt/ezrec-backend/backend/venv/bin/python3 video_worker.py (code=exited, status=1/FAILURE)
   Main PID: 12688 (code=exited, status=1/FAILURE)
        CPU: 544ms

● ezrec-api.service - EZREC FastAPI Backend
     Loaded: loaded (/etc/systemd/system/ezrec-api.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Tue 2025-07-29 21:22:04 EDT; 8s ago
    Process: 12675 ExecStart=/opt/ezrec-backend/api/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000 (code=exited, status=1/FAILURE)
   Main PID: 12675 (code=exited, status=1/FAILURE)
        CPU: 1.148s
Jul 29 21:22:03 raspberrypi uvicorn[12675]:            ^^^^^^^^^^^^^^^^^^
Jul 29 21:22:03 raspberrypi uvicorn[12675]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 29 21:22:03 raspberrypi uvicorn[12675]:     client = cls(supabase_url, supabase_key, options)
Jul 29 21:22:03 raspberrypi uvicorn[12675]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:03 raspberrypi uvicorn[12675]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 59, in __init__
Jul 29 21:22:03 raspberrypi uvicorn[12675]:     raise SupabaseException("Invalid URL")
Jul 29 21:22:03 raspberrypi uvicorn[12675]: supabase._sync.client.SupabaseException: Invalid URL
Jul 29 21:22:04 raspberrypi systemd[1]: ezrec-api.service: Main process exited, code=exited, status=1/FAILURE
Jul 29 21:22:04 raspberrypi systemd[1]: ezrec-api.service: Failed with result 'exit-code'.
Jul 29 21:22:04 raspberrypi systemd[1]: ezrec-api.service: Consumed 1.148s CPU time.
Jul 29 21:22:14 raspberrypi systemd[1]: ezrec-api.service: Scheduled restart job, restart counter is at 22.
Jul 29 21:22:14 raspberrypi systemd[1]: Stopped ezrec-api.service - EZREC FastAPI Backend.
Jul 29 21:22:14 raspberrypi systemd[1]: ezrec-api.service: Consumed 1.148s CPU time.
Jul 29 21:22:14 raspberrypi systemd[1]: Started ezrec-api.service - EZREC FastAPI Backend.
Jul 29 21:22:14 raspberrypi uvicorn[12704]: Traceback (most recent call last):
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/bin/uvicorn", line 8, in <module>
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     sys.exit(main())
Jul 29 21:22:14 raspberrypi uvicorn[12704]:              ^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 1442, in __call__
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     return self.main(*args, **kwargs)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 1363, in main
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     rv = self.invoke(ctx)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:          ^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 1226, in invoke
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     return ctx.invoke(self.callback, **ctx.params)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 794, in invoke
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     return callback(*args, **kwargs)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:            ^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/main.py", line 413, in main
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     run(
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/main.py", line 580, in run
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     server.run()
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 67, in run
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     return asyncio.run(self.serve(sockets=sockets))
Jul 29 21:22:14 raspberrypi uvicorn[12704]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/usr/lib/python3.11/asyncio/runners.py", line 190, in run
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     return runner.run(main)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:            ^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/usr/lib/python3.11/asyncio/runners.py", line 118, in run
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     return self._loop.run_until_complete(task)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/usr/lib/python3.11/asyncio/base_events.py", line 653, in run_until_complete
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     return future.result()
Jul 29 21:22:14 raspberrypi uvicorn[12704]:            ^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 71, in serve
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     await self._serve(sockets)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 78, in _serve
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     config.load()
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/config.py", line 436, in load
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     self.loaded_app = import_from_string(self.app)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/importer.py", line 19, in import_from_string
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     module = importlib.import_module(module_str)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/usr/lib/python3.11/importlib/__init__.py", line 126, in import_module
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     return _bootstrap._gcd_import(name[level:], package, level)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "<frozen importlib._bootstrap>", line 1206, in _gcd_import
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "<frozen importlib._bootstrap>", line 1178, in _find_and_load
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "<frozen importlib._bootstrap>", line 1149, in _find_and_load_unlocked
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "<frozen importlib._bootstrap_external>", line 940, in exec_module
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/api_server.py", line 58, in <module>
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
Jul 29 21:22:14 raspberrypi uvicorn[12704]:                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     return SyncClient.create(
Jul 29 21:22:14 raspberrypi uvicorn[12704]:            ^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     client = cls(supabase_url, supabase_key, options)
Jul 29 21:22:14 raspberrypi uvicorn[12704]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:14 raspberrypi uvicorn[12704]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 59, in __init__
Jul 29 21:22:14 raspberrypi uvicorn[12704]:     raise SupabaseException("Invalid URL")
Jul 29 21:22:14 raspberrypi uvicorn[12704]: supabase._sync.client.SupabaseException: Invalid URL
Jul 29 21:22:15 raspberrypi systemd[1]: ezrec-api.service: Main process exited, code=exited, status=1/FAILURE
Jul 29 21:22:15 raspberrypi systemd[1]: ezrec-api.service: Failed with result 'exit-code'.
Jul 29 21:22:15 raspberrypi systemd[1]: ezrec-api.service: Consumed 1.145s CPU time.
Jul 29 21:22:25 raspberrypi systemd[1]: ezrec-api.service: Scheduled restart job, restart counter is at 23.
Jul 29 21:22:25 raspberrypi systemd[1]: Stopped ezrec-api.service - EZREC FastAPI Backend.
Jul 29 21:22:25 raspberrypi systemd[1]: ezrec-api.service: Consumed 1.145s CPU time.
Jul 29 21:22:25 raspberrypi systemd[1]: Started ezrec-api.service - EZREC FastAPI Backend.
Jul 29 21:22:25 raspberrypi uvicorn[12725]: Traceback (most recent call last):
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/bin/uvicorn", line 8, in <module>
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     sys.exit(main())
Jul 29 21:22:25 raspberrypi uvicorn[12725]:              ^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 1442, in __call__
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     return self.main(*args, **kwargs)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 1363, in main
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     rv = self.invoke(ctx)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:          ^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 1226, in invoke
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     return ctx.invoke(self.callback, **ctx.params)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/click/core.py", line 794, in invoke
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     return callback(*args, **kwargs)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:            ^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/main.py", line 413, in main
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     run(
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/main.py", line 580, in run
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     server.run()
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 67, in run
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     return asyncio.run(self.serve(sockets=sockets))
Jul 29 21:22:25 raspberrypi uvicorn[12725]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/usr/lib/python3.11/asyncio/runners.py", line 190, in run
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     return runner.run(main)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:            ^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/usr/lib/python3.11/asyncio/runners.py", line 118, in run
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     return self._loop.run_until_complete(task)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/usr/lib/python3.11/asyncio/base_events.py", line 653, in run_until_complete
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     return future.result()
Jul 29 21:22:25 raspberrypi uvicorn[12725]:            ^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 71, in serve
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     await self._serve(sockets)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 78, in _serve
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     config.load()
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/config.py", line 436, in load
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     self.loaded_app = import_from_string(self.app)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/importer.py", line 19, in import_from_string
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     module = importlib.import_module(module_str)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/usr/lib/python3.11/importlib/__init__.py", line 126, in import_module
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     return _bootstrap._gcd_import(name[level:], package, level)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "<frozen importlib._bootstrap>", line 1206, in _gcd_import
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "<frozen importlib._bootstrap>", line 1178, in _find_and_load
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "<frozen importlib._bootstrap>", line 1149, in _find_and_load_unlocked
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "<frozen importlib._bootstrap_external>", line 940, in exec_module
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/api_server.py", line 58, in <module>
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
Jul 29 21:22:25 raspberrypi uvicorn[12725]:                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     return SyncClient.create(
Jul 29 21:22:25 raspberrypi uvicorn[12725]:            ^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     client = cls(supabase_url, supabase_key, options)
Jul 29 21:22:25 raspberrypi uvicorn[12725]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:25 raspberrypi uvicorn[12725]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 59, in __init__
Jul 29 21:22:25 raspberrypi uvicorn[12725]:     raise SupabaseException("Invalid URL")
Jul 29 21:22:25 raspberrypi uvicorn[12725]: supabase._sync.client.SupabaseException: Invalid URL
Jul 29 21:22:26 raspberrypi systemd[1]: ezrec-api.service: Main process exited, code=exited, status=1/FAILURE
Jul 29 21:22:26 raspberrypi systemd[1]: ezrec-api.service: Failed with result 'exit-code'.
Jul 29 21:22:26 raspberrypi systemd[1]: ezrec-api.service: Consumed 1.146s CPU time.
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $    ls -la /opt/ezrec-backend/api/venv/
   ls -la /opt/ezrec-backend/backend/venv/
total 24
drwxr-xr-x 5 ezrec ezrec 4096 Jul 29 21:18 .
drwxr-xr-x 6 root  root  4096 Jul 29 21:18 ..
drwxr-xr-x 3 ezrec ezrec 4096 Jul 29 21:19 bin
drwxr-xr-x 3 ezrec ezrec 4096 Jul 29 21:18 include
drwxr-xr-x 3 ezrec ezrec 4096 Jul 29 21:18 lib
lrwxrwxrwx 1 ezrec ezrec    3 Jul 29 21:18 lib64 -> lib
-rw-r--r-- 1 ezrec ezrec  166 Jul 29 21:18 pyvenv.cfg
total 24
drwxr-xr-x 5 ezrec ezrec 4096 Jul 29 21:19 .
drwxr-xr-x 4 root  root  4096 Jul 29 21:19 ..
drwxr-xr-x 3 ezrec ezrec 4096 Jul 29 21:20 bin
drwxr-xr-x 3 ezrec ezrec 4096 Jul 29 21:19 include
drwxr-xr-x 3 ezrec ezrec 4096 Jul 29 21:19 lib
lrwxrwxrwx 1 ezrec ezrec    3 Jul 29 21:19 lib64 -> lib
-rw-r--r-- 1 ezrec ezrec  193 Jul 29 21:19 pyvenv.cfg
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $    /opt/ezrec-backend/api/venv/bin/python3 -c "import fastapi, uvicorn"
   /opt/ezrec-backend/backend/venv/bin/python3 -c "import psutil, boto3"
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $    sudo journalctl -u ezrec-api.service -n 50
   sudo journalctl -u dual_recorder.service -n 50
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 67, in run
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     return asyncio.run(self.serve(sockets=sockets))
Jul 29 21:22:37 raspberrypi uvicorn[12743]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/usr/lib/python3.11/asyncio/runners.py", line 190, in run
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     return runner.run(main)
Jul 29 21:22:37 raspberrypi uvicorn[12743]:            ^^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/usr/lib/python3.11/asyncio/runners.py", line 118, in run
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     return self._loop.run_until_complete(task)
Jul 29 21:22:37 raspberrypi uvicorn[12743]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/usr/lib/python3.11/asyncio/base_events.py", line 653, in run_until_complete
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     return future.result()
Jul 29 21:22:37 raspberrypi uvicorn[12743]:            ^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 71, in serve
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     await self._serve(sockets)
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/server.py", line 78, in _serve
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     config.load()
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/config.py", line 436, in load
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     self.loaded_app = import_from_string(self.app)
Jul 29 21:22:37 raspberrypi uvicorn[12743]:                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/uvicorn/importer.py", line 19, in import_from_string
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     module = importlib.import_module(module_str)
Jul 29 21:22:37 raspberrypi uvicorn[12743]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/usr/lib/python3.11/importlib/__init__.py", line 126, in import_module
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     return _bootstrap._gcd_import(name[level:], package, level)
Jul 29 21:22:37 raspberrypi uvicorn[12743]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "<frozen importlib._bootstrap>", line 1206, in _gcd_import
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "<frozen importlib._bootstrap>", line 1178, in _find_and_load
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "<frozen importlib._bootstrap>", line 1149, in _find_and_load_unlocked
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "<frozen importlib._bootstrap_external>", line 940, in exec_module
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/opt/ezrec-backend/api/api_server.py", line 58, in <module>
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
Jul 29 21:22:37 raspberrypi uvicorn[12743]:                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     return SyncClient.create(
Jul 29 21:22:37 raspberrypi uvicorn[12743]:            ^^^^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     client = cls(supabase_url, supabase_key, options)
Jul 29 21:22:37 raspberrypi uvicorn[12743]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:37 raspberrypi uvicorn[12743]:   File "/opt/ezrec-backend/api/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 59, in __init__
Jul 29 21:22:37 raspberrypi uvicorn[12743]:     raise SupabaseException("Invalid URL")
Jul 29 21:22:37 raspberrypi uvicorn[12743]: supabase._sync.client.SupabaseException: Invalid URL
Jul 29 21:22:37 raspberrypi systemd[1]: ezrec-api.service: Main process exited, code=exited, status=1/FAILURE
Jul 29 21:22:37 raspberrypi systemd[1]: ezrec-api.service: Failed with result 'exit-code'.
Jul 29 21:22:37 raspberrypi systemd[1]: ezrec-api.service: Consumed 1.198s CPU time.
Jul 29 21:22:47 raspberrypi systemd[1]: ezrec-api.service: Scheduled restart job, restart counter is at 25.
Jul 29 21:22:47 raspberrypi systemd[1]: Stopped ezrec-api.service - EZREC FastAPI Backend.
Jul 29 21:22:47 raspberrypi systemd[1]: ezrec-api.service: Consumed 1.198s CPU time.
Jul 29 21:22:47 raspberrypi systemd[1]: Started ezrec-api.service - EZREC FastAPI Backend.
Jul 29 21:22:20 raspberrypi python3[12714]:     return SyncClient.create(
Jul 29 21:22:20 raspberrypi python3[12714]:            ^^^^^^^^^^^^^^^^^^
Jul 29 21:22:20 raspberrypi python3[12714]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 29 21:22:20 raspberrypi python3[12714]:     client = cls(supabase_url, supabase_key, options)
Jul 29 21:22:20 raspberrypi python3[12714]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:20 raspberrypi python3[12714]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
Jul 29 21:22:20 raspberrypi python3[12714]:     raise SupabaseException("supabase_key is required")
Jul 29 21:22:20 raspberrypi python3[12714]: supabase._sync.client.SupabaseException: supabase_key is required
Jul 29 21:22:20 raspberrypi systemd[1]: dual_recorder.service: Main process exited, code=exited, status=1/FAILURE
Jul 29 21:22:20 raspberrypi systemd[1]: dual_recorder.service: Failed with result 'exit-code'.
Jul 29 21:22:30 raspberrypi systemd[1]: dual_recorder.service: Scheduled restart job, restart counter is at 25.
Jul 29 21:22:30 raspberrypi systemd[1]: Stopped dual_recorder.service - EZREC Dual Camera Recorder Service.
Jul 29 21:22:30 raspberrypi systemd[1]: Started dual_recorder.service - EZREC Dual Camera Recorder Service.
Jul 29 21:22:31 raspberrypi python3[12732]: Traceback (most recent call last):
Jul 29 21:22:31 raspberrypi python3[12732]:   File "/opt/ezrec-backend/backend/dual_recorder.py", line 77, in <module>
Jul 29 21:22:31 raspberrypi python3[12732]:     from booking_utils import update_booking_status
Jul 29 21:22:31 raspberrypi python3[12732]:   File "/opt/ezrec-backend/api/booking_utils.py", line 17, in <module>
Jul 29 21:22:31 raspberrypi python3[12732]:     supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
Jul 29 21:22:31 raspberrypi python3[12732]:                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:31 raspberrypi python3[12732]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
Jul 29 21:22:31 raspberrypi python3[12732]:     return SyncClient.create(
Jul 29 21:22:31 raspberrypi python3[12732]:            ^^^^^^^^^^^^^^^^^^
Jul 29 21:22:31 raspberrypi python3[12732]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 29 21:22:31 raspberrypi python3[12732]:     client = cls(supabase_url, supabase_key, options)
Jul 29 21:22:31 raspberrypi python3[12732]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:31 raspberrypi python3[12732]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
Jul 29 21:22:31 raspberrypi python3[12732]:     raise SupabaseException("supabase_key is required")
Jul 29 21:22:31 raspberrypi python3[12732]: supabase._sync.client.SupabaseException: supabase_key is required
Jul 29 21:22:31 raspberrypi systemd[1]: dual_recorder.service: Main process exited, code=exited, status=1/FAILURE
Jul 29 21:22:31 raspberrypi systemd[1]: dual_recorder.service: Failed with result 'exit-code'.
Jul 29 21:22:41 raspberrypi systemd[1]: dual_recorder.service: Scheduled restart job, restart counter is at 26.
Jul 29 21:22:41 raspberrypi systemd[1]: Stopped dual_recorder.service - EZREC Dual Camera Recorder Service.
Jul 29 21:22:41 raspberrypi systemd[1]: Started dual_recorder.service - EZREC Dual Camera Recorder Service.
Jul 29 21:22:41 raspberrypi python3[12755]: Traceback (most recent call last):
Jul 29 21:22:41 raspberrypi python3[12755]:   File "/opt/ezrec-backend/backend/dual_recorder.py", line 77, in <module>
Jul 29 21:22:41 raspberrypi python3[12755]:     from booking_utils import update_booking_status
Jul 29 21:22:41 raspberrypi python3[12755]:   File "/opt/ezrec-backend/api/booking_utils.py", line 17, in <module>
Jul 29 21:22:41 raspberrypi python3[12755]:     supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
Jul 29 21:22:41 raspberrypi python3[12755]:                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:41 raspberrypi python3[12755]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 369, in create_client
Jul 29 21:22:41 raspberrypi python3[12755]:     return SyncClient.create(
Jul 29 21:22:41 raspberrypi python3[12755]:            ^^^^^^^^^^^^^^^^^^
Jul 29 21:22:41 raspberrypi python3[12755]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 101, in create
Jul 29 21:22:41 raspberrypi python3[12755]:     client = cls(supabase_url, supabase_key, options)
Jul 29 21:22:41 raspberrypi python3[12755]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Jul 29 21:22:41 raspberrypi python3[12755]:   File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 55, in __init__
Jul 29 21:22:41 raspberrypi python3[12755]:     raise SupabaseException("supabase_key is required")
Jul 29 21:22:41 raspberrypi python3[12755]: supabase._sync.client.SupabaseException: supabase_key is required
Jul 29 21:22:41 raspberrypi systemd[1]: dual_recorder.service: Main process exited, code=exited, status=1/FAILURE
Jul 29 21:22:41 raspberrypi systemd[1]: dual_recorder.service: Failed with result 'exit-code'.
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ 

