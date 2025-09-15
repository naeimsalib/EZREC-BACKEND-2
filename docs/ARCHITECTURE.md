# EZREC Architecture Documentation

**Comprehensive technical documentation of the EZREC dual-camera recording system architecture**

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Service Architecture](#service-architecture)
- [Data Flow](#data-flow)
- [Configuration Management](#configuration-management)
- [Error Handling](#error-handling)
- [Logging System](#logging-system)
- [Security Considerations](#security-considerations)
- [Performance Characteristics](#performance-characteristics)
- [Scalability](#scalability)

## System Overview

EZREC is built using a **modern service-oriented architecture** that separates concerns and provides clean interfaces between components. The system is designed for reliability, maintainability, and scalability.

### **Core Principles**

- **Separation of Concerns**: Each service has a single responsibility
- **Dependency Injection**: Services are loosely coupled and easily testable
- **Configuration Management**: Centralized configuration with environment-specific overrides
- **Error Handling**: Structured exception handling with retry logic
- **Observability**: Comprehensive logging and monitoring
- **Fault Tolerance**: Graceful degradation and automatic recovery

### **Technology Stack**

- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **Database**: Supabase (PostgreSQL)
- **Storage**: AWS S3
- **Camera Interface**: rpicam-vid, libcamera
- **Video Processing**: FFmpeg
- **Service Management**: systemd
- **Configuration**: python-dotenv, dataclasses

## Service Architecture

### **Service Layer**

The service layer contains the core business logic and is organized into specialized services:

```
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
├─────────────────────────────────────────────────────────────┤
│  Camera Service  │  Booking Service  │  Video Processor    │
│                  │                   │                     │
│  • Detection     │  • Management     │  • Merging          │
│  • Recording     │  • Status Track   │  • Validation       │
│  • Control       │  • Scheduling     │  • Compression      │
├─────────────────────────────────────────────────────────────┤
│  Upload Manager  │  System Monitor   │  Configuration      │
│                  │                   │                     │
│  • S3 Uploads    │  • Health Checks  │  • Settings Mgmt    │
│  • Progress      │  • Metrics        │  • Environment      │
│  • Cleanup       │  • Alerts         │  • Validation       │
└─────────────────────────────────────────────────────────────┘
```

### **Service Details**

#### **Camera Service** (`services/camera_service.py`)
- **Responsibility**: Camera detection, recording operations, and camera control
- **Key Methods**:
  - `detect_cameras()`: Enumerate available cameras
  - `record_camera()`: Record from a specific camera
  - `start_recording_session()`: Start multi-camera recording
  - `stop_recording_session()`: Stop all recording operations
- **Dependencies**: rpicam-vid, subprocess, threading

#### **Booking Service** (`services/booking_service.py`)
- **Responsibility**: Booking lifecycle management and status tracking
- **Key Methods**:
  - `find_active_booking()`: Find bookings that should be recording now
  - `create_booking()`: Create new booking records
  - `update_booking_status()`: Update booking status
  - `cleanup_expired_bookings()`: Remove old bookings
- **Dependencies**: Supabase, local JSON cache

#### **Video Processor** (`services/video_processor.py`)
- **Responsibility**: Video processing, merging, and validation
- **Key Methods**:
  - `merge_videos()`: Merge multiple video files
  - `validate_video()`: Check video file integrity
  - `compress_video()`: Optimize video file size
- **Dependencies**: FFmpeg, OpenCV (optional)

#### **Upload Manager** (`services/upload_manager.py`)
- **Responsibility**: File uploads to cloud storage
- **Key Methods**:
  - `upload_to_s3()`: Upload files to S3
  - `upload_video()`: Upload video with standardized naming
  - `generate_presigned_url()`: Create temporary access URLs
- **Dependencies**: boto3, AWS S3

### **Configuration System** (`config/settings.py`)

The configuration system provides a centralized way to manage all application settings:

```python
@dataclass
class Settings:
    database: DatabaseConfig
    storage: StorageConfig
    camera: CameraConfig
    paths: PathConfig
    logging: LoggingConfig
    api: APIConfig
```

**Benefits**:
- Single source of truth for all configuration
- Type-safe configuration with validation
- Environment-specific overrides
- Lazy initialization of expensive resources

### **Utility Layer** (`utils/`)

#### **Logging System** (`utils/logger.py`)
- **Standardized Logging**: Consistent format across all services
- **Color-coded Output**: Different colors for different log levels
- **File and Console Output**: Configurable output destinations
- **Context Management**: Add context to log messages
- **Performance Decorators**: Log function execution time

#### **Exception Handling** (`utils/exceptions.py`)
- **Structured Exceptions**: Custom exception hierarchy
- **Error Context**: Rich error information with details
- **Retry Logic**: Automatic retry for transient errors
- **Error Conversion**: Convert generic exceptions to structured ones

## Data Flow

### **Recording Workflow**

```
1. Booking Created
   ↓
2. Booking Service finds active booking
   ↓
3. Camera Service detects available cameras
   ↓
4. Recording starts on all cameras simultaneously
   ↓
5. Raw video files saved to local storage
   ↓
6. Video Processor merges dual camera feeds
   ↓
7. Upload Manager transfers to S3
   ↓
8. Booking status updated to 'completed'
   ↓
9. Local files cleaned up
```

### **Service Communication**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   API       │    │   Dual      │    │   Video     │
│   Server    │◄──►│  Recorder   │◄──►│   Worker    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Booking    │    │   Camera    │    │   Upload    │
│  Service    │    │   Service   │    │   Manager   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Supabase   │    │  rpicam-vid │    │   AWS S3    │
│  Database   │    │   Cameras   │    │   Storage   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### **Data Storage**

#### **Local Storage**
- **Recordings**: `/opt/ezrec-backend/recordings/`
- **Bookings**: `/opt/ezrec-backend/api/local_data/bookings.json`
- **Logs**: `/opt/ezrec-backend/logs/`
- **Configuration**: `/opt/ezrec-backend/.env`

#### **Cloud Storage**
- **Database**: Supabase (PostgreSQL)
- **Files**: AWS S3
- **Metadata**: Stored in database with S3 references

## Configuration Management

### **Configuration Hierarchy**

1. **Default Values**: Hardcoded in `config/settings.py`
2. **Environment Variables**: Override defaults from `.env` file
3. **Runtime Configuration**: Dynamic configuration changes

### **Configuration Categories**

#### **Database Configuration**
```python
@dataclass
class DatabaseConfig:
    supabase_url: str
    supabase_key: str
    
    def validate(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)
```

#### **Storage Configuration**
```python
@dataclass
class StorageConfig:
    aws_access_key: str
    aws_secret_key: str
    aws_region: str
    s3_bucket: str
```

#### **Camera Configuration**
```python
@dataclass
class CameraConfig:
    recording_width: int = 1280
    recording_height: int = 720
    recording_framerate: int = 30
    recording_timeout: int = 300000
```

### **Environment-Specific Configuration**

- **Development**: Debug logging, local storage
- **Testing**: Mock services, temporary storage
- **Production**: Optimized settings, cloud storage

## Error Handling

### **Exception Hierarchy**

```
EZRECException (Base)
├── CameraError
│   ├── CameraNotAvailableError
│   ├── CameraInitializationError
│   └── RecordingError
├── BookingError
│   ├── BookingNotFoundError
│   ├── BookingValidationError
│   └── BookingConflictError
├── VideoProcessingError
│   ├── VideoMergeError
│   └── VideoValidationError
├── UploadError
│   └── S3UploadError
├── ConfigurationError
├── DatabaseError
├── ServiceError
└── RetryableError
```

### **Error Handling Strategies**

#### **Retry Logic**
```python
@retry(max_attempts=3, backoff_factor=2)
def upload_to_s3(self, file_path: Path) -> bool:
    # Upload implementation with automatic retry
    pass
```

#### **Graceful Degradation**
- Camera failures: Continue with available cameras
- Upload failures: Retry with exponential backoff
- Database failures: Use local cache

#### **Error Recovery**
- Automatic service restart on critical failures
- Health checks and self-healing
- Manual intervention alerts

## Logging System

### **Logging Architecture**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Service   │    │   Logger    │    │   Output    │
│   Code      │───►│   Utility   │───►│  Destinations│
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │   Log       │
                   │  Processing │
                   └─────────────┘
```

### **Log Levels**

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about system operation
- **WARNING**: Something unexpected happened
- **ERROR**: A serious problem occurred
- **CRITICAL**: A very serious error occurred

### **Log Format**

```
2025-01-14 10:30:00,123 - camera_service - INFO - Camera 0 detected
2025-01-14 10:30:01,456 - booking_service - WARNING - No active booking found
2025-01-14 10:30:02,789 - upload_manager - ERROR - S3 upload failed: Connection timeout
```

### **Log Destinations**

- **Console**: Real-time monitoring during development
- **Files**: Persistent storage for production
- **System Logs**: Integration with systemd journal

## Security Considerations

### **Authentication & Authorization**

- **API Keys**: Secure storage of Supabase and AWS credentials
- **Service Accounts**: Dedicated IAM users with minimal permissions
- **Environment Variables**: Sensitive data in environment variables only

### **Data Protection**

- **Encryption in Transit**: HTTPS for all API communications
- **Encryption at Rest**: S3 server-side encryption
- **Access Control**: IAM policies for S3 bucket access
- **Audit Logging**: Comprehensive logging of all operations

### **Network Security**

- **Firewall**: Restrict access to necessary ports only
- **VPN**: Secure remote access to production systems
- **SSL/TLS**: Encrypted communications

### **Application Security**

- **Input Validation**: Validate all user inputs
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Sanitize user-generated content
- **Rate Limiting**: Prevent abuse of API endpoints

## Performance Characteristics

### **Recording Performance**

- **Latency**: < 100ms camera initialization
- **Throughput**: 30 FPS at 1280x720 resolution
- **Storage**: ~100MB/minute per camera
- **CPU Usage**: 20-30% on Raspberry Pi 4

### **Processing Performance**

- **Video Merging**: 2-3x real-time (2-minute video merges in ~1 minute)
- **Upload Speed**: Limited by network bandwidth
- **Memory Usage**: < 512MB per service

### **Scalability Limits**

- **Concurrent Recordings**: Limited by camera hardware
- **Storage**: Limited by local disk space
- **Network**: Limited by upload bandwidth
- **Processing**: Limited by CPU cores

## Scalability

### **Horizontal Scaling**

- **Multiple Pi Units**: Deploy on multiple Raspberry Pi devices
- **Load Balancing**: Distribute recordings across devices
- **Centralized Management**: Single API server managing multiple recorders

### **Vertical Scaling**

- **Higher-end Hardware**: Use more powerful single-board computers
- **Storage Expansion**: Add external storage devices
- **Network Upgrades**: Increase bandwidth for faster uploads

### **Service Scaling**

- **Microservices**: Split services across multiple containers
- **Database Scaling**: Use read replicas for better performance
- **Storage Scaling**: Use multiple S3 buckets or regions

### **Future Enhancements**

- **Container Orchestration**: Kubernetes deployment
- **Message Queues**: Asynchronous processing with Redis/RabbitMQ
- **Caching**: Redis for frequently accessed data
- **CDN**: CloudFront for video delivery

---

**This architecture documentation provides a comprehensive understanding of the EZREC system design and implementation details.**
