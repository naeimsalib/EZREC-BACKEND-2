michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $    chmod +x master_fix_v2.sh
   sudo ./master_fix_v2.sh
🔧 EZREC Master Fix Script v2
==============================

🔄 Step 1: Installing libcamera Python binding...
🔧 Installing libcamera Python binding...
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
python3-libcamera is already the newest version (0.5.1+rpt20250722-1).
libcamera-apps is already the newest version (1.8.1-1~bookworm).
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
✅ libcamera installation completed
🔍 Testing libcamera import...
✅ libcamera import successful

🔄 Step 2: Fixing directory permissions and ownership...
🔐 Fixing directory permissions and ownership...
✅ Directory permissions and ownership fixed
🔍 Testing write permissions...
✅ Write permissions working

🔄 Step 3: system_status.service already fixed

🔄 Step 4: Installing ImageMagick for logo generation...
🎨 Installing ImageMagick for logo generation...
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
imagemagick is already the newest version (8:6.9.11.60+dfsg-1.6+deb12u3).
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
✅ ImageMagick installation completed
🔍 Testing ImageMagick...
Version: ImageMagick 6.9.11-60 Q16 aarch64 2021-01-25 https://imagemagick.org
Copyright: (C) 1999-2021 ImageMagick Studio LLC
License: https://imagemagick.org/script/license.php
Features: Cipher DPC Modules OpenMP(4.5) 
Delegates (built-in): bzlib djvu fftw fontconfig freetype heic jbig jng jp2 jpeg lcms lqr ltdl lzma openexr pangocairo png tiff webp wmf x xml zlib
✅ ImageMagick working

🔄 Step 5: Fixing backend virtual environment libcamera import...
🔧 Fixing backend virtual environment libcamera import...
🧹 Removing existing backend virtual environment...
📦 Creating new backend virtual environment...
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
📦 Installing system packages...
Hit:1 http://deb.debian.org/debian bookworm InRelease
Hit:2 http://deb.debian.org/debian-security bookworm-security InRelease
Hit:3 http://deb.debian.org/debian bookworm-updates InRelease
Hit:4 http://archive.raspberrypi.com/debian bookworm InRelease
Reading package lists... Done
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
python3-libcamera is already the newest version (0.5.1+rpt20250722-1).
python3-picamera2 is already the newest version (0.3.30-1).
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
📦 Installing Python packages...
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
🧪 Testing libcamera import...
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'libcamera'
❌ libcamera import failed, trying alternative installation...
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Collecting picamera2
  Using cached picamera2-0.3.30-py3-none-any.whl.metadata (6.4 kB)
Collecting PiDNG (from picamera2)
  Using cached pidng-4.0.9-cp311-cp311-linux_aarch64.whl
Collecting av (from picamera2)
  Using cached av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl.metadata (4.6 kB)
Collecting jsonschema (from picamera2)
  Using cached jsonschema-4.25.0-py3-none-any.whl.metadata (7.7 kB)
Collecting libarchive-c (from picamera2)
  Using cached libarchive_c-5.3-py3-none-any.whl.metadata (5.8 kB)
Collecting numpy (from picamera2)
  Downloading numpy-2.3.2-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl.metadata (62 kB)
Collecting piexif (from picamera2)
  Using cached https://www.piwheels.org/simple/piexif/piexif-1.1.3-py2.py3-none-any.whl (20 kB)
Collecting pillow (from picamera2)
  Using cached pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl.metadata (9.0 kB)
Collecting python-prctl (from picamera2)
  Using cached python_prctl-1.8.1-cp311-cp311-linux_aarch64.whl
Collecting simplejpeg (from picamera2)
  Using cached simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (32 kB)
Collecting tqdm (from picamera2)
  Using cached https://www.piwheels.org/simple/tqdm/tqdm-4.67.1-py3-none-any.whl (78 kB)
Collecting videodev2 (from picamera2)
  Using cached videodev2-0.0.4-py3-none-any.whl.metadata (2.8 kB)
Collecting attrs>=22.2.0 (from jsonschema->picamera2)
  Using cached https://www.piwheels.org/simple/attrs/attrs-25.3.0-py3-none-any.whl (63 kB)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema->picamera2)
  Using cached jsonschema_specifications-2025.4.1-py3-none-any.whl.metadata (2.9 kB)
Collecting referencing>=0.28.4 (from jsonschema->picamera2)
  Using cached https://www.piwheels.org/simple/referencing/referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting rpds-py>=0.7.1 (from jsonschema->picamera2)
  Using cached rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.2 kB)
Collecting typing-extensions>=4.4.0 (from referencing>=0.28.4->jsonschema->picamera2)
  Using cached typing_extensions-4.14.1-py3-none-any.whl.metadata (3.0 kB)
Using cached picamera2-0.3.30-py3-none-any.whl (121 kB)
Using cached av-15.0.0-cp311-cp311-manylinux_2_28_aarch64.whl (38.2 MB)
Using cached jsonschema-4.25.0-py3-none-any.whl (89 kB)
Using cached jsonschema_specifications-2025.4.1-py3-none-any.whl (18 kB)
Using cached rpds_py-0.26.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (381 kB)
Using cached typing_extensions-4.14.1-py3-none-any.whl (43 kB)
Using cached libarchive_c-5.3-py3-none-any.whl (17 kB)
Downloading numpy-2.3.2-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl (14.6 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.6/14.6 MB 4.1 MB/s eta 0:00:00
Using cached pillow-11.3.0-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl (6.0 MB)
Using cached simplejpeg-1.8.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (446 kB)
Using cached videodev2-0.0.4-py3-none-any.whl (49 kB)
Installing collected packages: python-prctl, libarchive-c, videodev2, typing-extensions, tqdm, rpds-py, pillow, piexif, numpy, av, attrs, simplejpeg, referencing, PiDNG, jsonschema-specifications, jsonschema, picamera2
  Attempting uninstall: python-prctl
    Found existing installation: python-prctl 1.8.1
    Uninstalling python-prctl-1.8.1:
      Successfully uninstalled python-prctl-1.8.1
  Attempting uninstall: libarchive-c
    Found existing installation: libarchive-c 5.3
    Uninstalling libarchive-c-5.3:
      Successfully uninstalled libarchive-c-5.3
  Attempting uninstall: videodev2
    Found existing installation: videodev2 0.0.4
    Uninstalling videodev2-0.0.4:
      Successfully uninstalled videodev2-0.0.4
  Attempting uninstall: typing-extensions
    Found existing installation: typing_extensions 4.14.1
    Uninstalling typing_extensions-4.14.1:
      Successfully uninstalled typing_extensions-4.14.1
  Attempting uninstall: tqdm
    Found existing installation: tqdm 4.67.1
    Uninstalling tqdm-4.67.1:
      Successfully uninstalled tqdm-4.67.1
  Attempting uninstall: rpds-py
    Found existing installation: rpds-py 0.26.0
    Uninstalling rpds-py-0.26.0:
      Successfully uninstalled rpds-py-0.26.0
  Attempting uninstall: pillow
    Found existing installation: pillow 11.3.0
    Uninstalling pillow-11.3.0:
      Successfully uninstalled pillow-11.3.0
  Attempting uninstall: piexif
    Found existing installation: piexif 1.1.3
    Uninstalling piexif-1.1.3:
      Successfully uninstalled piexif-1.1.3
  Attempting uninstall: numpy
    Found existing installation: numpy 2.2.6
    Uninstalling numpy-2.2.6:
      Successfully uninstalled numpy-2.2.6
  Attempting uninstall: av
    Found existing installation: av 15.0.0
    Uninstalling av-15.0.0:
      Successfully uninstalled av-15.0.0
  Attempting uninstall: attrs
    Found existing installation: attrs 25.3.0
    Uninstalling attrs-25.3.0:
      Successfully uninstalled attrs-25.3.0
  Attempting uninstall: simplejpeg
    Found existing installation: simplejpeg 1.8.2
    Uninstalling simplejpeg-1.8.2:
      Successfully uninstalled simplejpeg-1.8.2
  Attempting uninstall: referencing
    Found existing installation: referencing 0.36.2
    Uninstalling referencing-0.36.2:
      Successfully uninstalled referencing-0.36.2
  Attempting uninstall: PiDNG
    Found existing installation: pidng 4.0.9
    Uninstalling pidng-4.0.9:
      Successfully uninstalled pidng-4.0.9
  Attempting uninstall: jsonschema-specifications
    Found existing installation: jsonschema-specifications 2025.4.1
    Uninstalling jsonschema-specifications-2025.4.1:
      Successfully uninstalled jsonschema-specifications-2025.4.1
  Attempting uninstall: jsonschema
    Found existing installation: jsonschema 4.25.0
    Uninstalling jsonschema-4.25.0:
      Successfully uninstalled jsonschema-4.25.0
  Attempting uninstall: picamera2
    Found existing installation: picamera2 0.3.30
    Uninstalling picamera2-0.3.30:
      Successfully uninstalled picamera2-0.3.30
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
opencv-python-headless 4.12.0.88 requires numpy<2.3.0,>=2; python_version >= "3.9", but you have numpy 2.3.2 which is incompatible.
Successfully installed PiDNG-4.0.9 attrs-25.3.0 av-15.0.0 jsonschema-4.25.0 jsonschema-specifications-2025.4.1 libarchive-c-5.3 numpy-2.3.2 picamera2-0.3.30 piexif-1.1.3 pillow-11.3.0 python-prctl-1.8.1 referencing-0.36.2 rpds-py-0.26.0 simplejpeg-1.8.2 tqdm-4.67.1 typing-extensions-4.14.1 videodev2-0.0.4
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'libcamera'
🧪 Testing picamera2 import...
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/picamera2/__init__.py", line 4, in <module>
    import libcamera
ModuleNotFoundError: No module named 'libcamera'
❌ picamera2 import failed
🔐 Setting ownership for services...
✅ Backend virtual environment fix completed

🔄 Step 6: Fixing API issues...
🔧 Fixing API issues...
📝 Creating bookings file...
✅ Initialized empty bookings file
🔐 Setting permissions...
🧪 Testing API endpoints...
🔍 Testing GET /bookings...
✅ GET /bookings working
   Response: []
🔍 Testing POST /bookings...
✅ POST /bookings working
   Response: {"message":"Successfully created 1 booking(s)","bookings":["test_123"]}
✅ API issues fix completed

🔄 Step 7: Smoke test video size threshold already fixed

🔄 Step 8: Restarting and verifying all services...
🚀 Restarting and verifying all services...
🔄 Reloading systemd...
🔄 Restarting services...
⏳ Waiting for services to start...
c
   python3 test_complete_system.py📊 Service Status:
==================

🔍 dual_recorder.service:
✅ dual_recorder.service is active

🔍 video_worker.service:
✅ video_worker.service is active

🔍 ezrec-api.service:
✅ ezrec-api.service is active

🔍 system_status.service:
❌ system_status.service is not active
📝 Recent logs:
c
   python3 test_complete_system.pyJul 29 21:47:15 raspberrypi python3[18933]: 2025-07-29 21:47:15,997 [ERROR] ❌ Error updating Supabase status: {'message': 'JSON could not be generated', 'code': 401, 'hint': 'Refer to full message for details', 'details': 'b\'{"message":"Invalid API key","hint":"Double check your Supabase `anon` or `service_role` API key."}\''}
Jul 29 21:47:15 raspberrypi python3[18933]: 2025-07-29 21:47:15,997 [INFO] ✅ Health check completed successfully
Jul 29 21:47:15 raspberrypi python3[18933]: 2025-07-29 21:47:15,997 [INFO] ✅ System Status: healthy
Jul 29 21:47:16 raspberrypi systemd[1]: system_status.service: Deactivated successfully.
Jul 29 21:47:16 raspberrypi systemd[1]: Finished system_status.service - EZREC System Status Monitor.

🌐 Testing API response...
✅ API server is responding
   Response: {"status":"running","timestamp":"2025-07-29T21:47:26.177025","version":"1.0.0"}

🎉 Service restart completed!

🔄 Step 9: Running end-to-end tests...
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
✅ dual_recorder.service: active
✅ video_worker.service: active
✅ ezrec-api.service: active


🧪 Testing API Endpoints...

🌐 Testing API Endpoints...
⏳ Waiting for API to start...
✅ API status endpoint working
   Response: {'status': 'running', 'timestamp': '2025-07-29T21:47:37.312016', 'version': '1.0.0'}
✅ API bookings endpoint working


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
✅ Booking creation working
   Response: {'message': 'Successfully created 1 booking(s)', 'bookings': ['test_complete_123']}

📊 Complete Test Results:
✅ Passed: 7/8
❌ Failed: 1/8

⚠️ Some tests failed. Check the output above for issues.

🔧 Troubleshooting:
1. Run: sudo ./fix_venv.sh
2. Check service logs: sudo journalctl -u ezrec-api.service -f
3. Restart services: sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service

🎉 Master fix v2 completed!
📋 Summary of fixes applied:
✅ Installed libcamera Python binding
✅ Fixed directory permissions and ownership
✅ Fixed system_status.service syntax
✅ Installed ImageMagick
✅ Fixed backend virtual environment libcamera import
✅ Fixed API issues (bookings file and JSON parsing)
✅ Fixed smoke test video size threshold
✅ Restarted all services
✅ Ran end-to-end tests
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
✅ dual_recorder.service: active
✅ video_worker.service: active
✅ ezrec-api.service: active


🧪 Testing API Endpoints...

🌐 Testing API Endpoints...
⏳ Waiting for API to start...
✅ API status endpoint working
   Response: {'status': 'running', 'timestamp': '2025-07-29T21:48:04.297817', 'version': '1.0.0'}
✅ API bookings endpoint working


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
✅ Booking creation working
   Response: {'message': 'Successfully created 1 booking(s)', 'bookings': ['test_complete_123']}

📊 Complete Test Results:
✅ Passed: 7/8
❌ Failed: 1/8

⚠️ Some tests failed. Check the output above for issues.

🔧 Troubleshooting:
1. Run: sudo ./fix_venv.sh
2. Check service logs: sudo journalctl -u ezrec-api.service -f
3. Restart services: sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ 
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ # Test backend venv imports
/opt/ezrec-backend/backend/venv/bin/python3 -c "import libcamera, picamera2; print('✅ Backend imports working')"

# Test API endpoints
curl http://localhost:8000/bookings
curl -X POST http://localhost:8000/bookings -H "Content-Type: application/json" -d '{"id":"test","user_id":"test","camera_id":"test","start_time":"2024-01-15T10:00:00","end_time":"2024-01-15T10:02:00","status":"STARTED"}'

# Run complete test
python3 test_complete_system.py
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'libcamera'
[{"id":"test_123","user_id":"test_user","start_time":"2024-01-15T10:00:00","end_time":"2024-01-15T10:02:00","date":null,"camera_id":"test_camera","recording_id":null,"email":null,"created_at":"2025-07-29T21:47:05.955080","updated_at":"2025-07-29T21:47:05.955088"},{"id":"test_complete_123","user_id":"test_user","start_time":"2024-01-15T10:00:00","end_time":"2024-01-15T10:02:00","date":null,"camera_id":"test_camera","recording_id":null,"email":null,"created_at":"2025-07-29T21:47:37.321523","updated_at":"2025-07-29T21:47:37.321530"},{"id":"test_complete_123","user_id":"test_user","start_time":"2024-01-15T10:00:00","end_time":"2024-01-15T10:02:00","date":null,"camera_id":"test_camera","recording_id":null,"email":null,"created_at":"2025-07-29T21:48:04.306893","updated_at":"2025-07-29T21:48:04.306900"}]{"message":"Successfully created 1 booking(s)","bookings":["test"]}🚀 EZREC Complete System Test
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
✅ dual_recorder.service: active
✅ video_worker.service: active
✅ ezrec-api.service: active


🧪 Testing API Endpoints...

🌐 Testing API Endpoints...
⏳ Waiting for API to start...
✅ API status endpoint working
   Response: {'status': 'running', 'timestamp': '2025-07-29T21:48:34.643487', 'version': '1.0.0'}
✅ API bookings endpoint working


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
✅ Booking creation working
   Response: {'message': 'Successfully created 1 booking(s)', 'bookings': ['test_complete_123']}

📊 Complete Test Results:
✅ Passed: 7/8
❌ Failed: 1/8

⚠️ Some tests failed. Check the output above for issues.

🔧 Troubleshooting:
1. Run: sudo ./fix_venv.sh
2. Check service logs: sudo journalctl -u ezrec-api.service -f
3. Restart services: sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service
michomanoly14892@raspberrypi:~/EZREC-BACKEND-2 $ 