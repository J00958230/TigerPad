# TigerPad Security and Deployment Guide

**Project:** TigerPad — JSU Career Accelerator  
**Institution:** Jackson State University  
**Project Team:** Digital Frontier  
**Frontend:** React, JavaScript, Vite  
**Backend:** Python, FastAPI  
**Database:** MySQL 8.x hosted on Aiven  
**Database ORM:** SQLAlchemy  
**Résumé Object Storage:** Cloudflare R2  
**Application Hosting:** Render  
**AI Provider:** Groq  
**AI Model:** `openai/gpt-oss-20b` (verify against current production configuration)

---

## 1. Purpose

TigerPad is a university-wide career-readiness website designed to help Jackson State University students, faculty, and administrators manage career development activities.

The system supports:

- Student career profiles
- Résumé management and résumé building
- Skills and certifications
- Student projects and professional experience
- Career-path recommendations
- AI-powered career guidance
- Faculty student reviews
- Administrator management
- Progress tracking
- Notifications
- Interview preparation

This document describes TigerPad's application architecture, security requirements, deployment configuration, operational procedures, and testing expectations.

**Important:** This guide documents the intended and reported deployment architecture. It is not proof that every listed security control has been implemented or tested. Production readiness requires verification of the application code, infrastructure configuration, and test results.

---

## 2. System Architecture

TigerPad uses a distributed web architecture.

```text
                  TIGERPAD ARCHITECTURE

                  Student / Faculty / Admin
                            |
                            | HTTPS
                            v
                  React + Vite Frontend
                     Hosted on Render
                            |
                            | HTTPS / REST API
                            v
                    FastAPI Backend
                     Hosted on Render
                            |
          +-----------------+------------------+
          |                 |                  |
          v                 v                  v
     Aiven MySQL       Cloudflare R2        Groq AI API
     Relational DB     Résumé Storage       AI Feedback
          |                 |                  |
          v                 v                  v
     User Accounts     Private Résumé       Résumé Analysis
     Student Profiles  Objects              Career Guidance
     Faculty Profiles  Storage Keys         Improvement Advice
     Career Paths
     Academic Data
     Audit Records
```

### 2.1 React Frontend

The frontend is responsible for:

- Displaying the TigerPad interface
- Collecting and validating user input
- Providing role-specific dashboards
- Sending requests to the backend API
- Displaying résumé feedback and career guidance
- Showing successful and failed operations

The frontend must not directly connect to MySQL, expose private Cloudflare R2 credentials, or contain the Groq API key.

### 2.2 FastAPI Backend

The backend is responsible for:

- Authentication and authorization
- Request validation
- Business logic
- Database operations
- Résumé upload and retrieval
- AI service integration
- Audit logging
- Error handling

### 2.3 Aiven MySQL

Aiven hosts TigerPad's relational MySQL database.

The database stores structured information, including user accounts, student profiles, faculty profiles, academic programs, career paths, permissions, and résumé metadata.

### 2.4 Cloudflare R2

Cloudflare R2 provides object storage for uploaded résumé documents.

The database stores the relationship between the student and the résumé, while the document itself is stored in the configured R2 bucket.

### 2.5 Groq AI

Groq provides AI inference for supported résumé analysis and career guidance functionality.

The backend communicates with Groq using credentials stored in its server-side environment.

### 2.6 Render

Render hosts the deployed TigerPad frontend and backend services.

Current project endpoints:

- Frontend: `https://tigerpad.onrender.com`
- Backend: `https://tigerpad-backend.onrender.com`
- Backend health endpoint: `https://tigerpad-backend.onrender.com/status`

---

## 3. Environment Configuration

TigerPad uses environment variables to manage deployment-specific settings and secrets.

Important project files include:

- `.env`
- `.env.example`
- `config.py`
- `main.py`

The `.env` file contains local configuration and potentially sensitive credentials.

The `.env.example` file should contain safe placeholders without actual secrets.

Never commit production credentials to GitHub.

### 3.1 Environment Variable Categories

The Render backend must be configured with the environment variables actually expected by TigerPad's current configuration code.

Typical categories include:

| Category | Configuration |
|---|---|
| Application | Production mode, debug setting, HTTPS configuration |
| Database | MySQL connection URL or individual connection settings |
| Authentication | JWT signing secret, token expiration settings |
| AI | Groq API key and model selection |
| Object storage | R2 endpoint, bucket, access key, secret key |
| Security | CORS origins, upload limits, scanning settings |

The exact environment variable names must match those read by `config.py` and the relevant service modules.

Do not assume that adding a variable to Render automatically enables a feature.

### 3.2 Git Security

Verify that `.gitignore` excludes:

```gitignore
.env
.env.*
!.env.example

__pycache__/
*.pyc
.venv/

uploads/
*.log
```

If credentials were previously committed to GitHub, rotate or revoke them.

Deleting a credential from the latest commit does not remove it from Git history.

### 3.3 Production Secrets

Use separate secrets for development and production.

Never expose:

- MySQL passwords
- JWT signing secrets
- Groq API keys
- Cloudflare R2 secret access keys
- Refresh tokens
- Private student information

---

## 4. Authentication Security

TigerPad supports three principal user roles:

1. Student
2. Faculty
3. Administrator

### 4.1 Password Security

Passwords must be stored as secure password hashes.

Recommended algorithms include:

- Argon2id
- bcrypt

Never store plaintext passwords.

Never log passwords or include them in error responses.

Password-reset tokens should be short-lived, single-use, and securely generated.

### 4.2 JWT Security

JWT authentication must validate:

- Token signature
- Expiration time
- Token type
- User identity
- Account status
- Authorized role

Recommended token settings from the original security guide:

- Access token: 30 minutes
- Refresh token: 7 days

These values must be checked against the deployed configuration before being described as actual production settings.

Refresh tokens should support revocation and rotation.

Production authentication tokens must use secure storage mechanisms appropriate to the application's threat model.

Avoid exposing long-lived sensitive tokens to JavaScript-accessible browser storage.

### 4.3 Account Lockout

Repeated failed login attempts should trigger temporary protection.

Recommended settings:

- Maximum attempts: 5
- Lockout duration: 15 minutes

Apply rate limiting to authentication endpoints.

Verify the implemented thresholds and lockout behavior through testing.

---

## 5. Role-Based Access Control

All protected endpoints must enforce authorization on the backend.

### 5.1 Student

Students may:

- Manage their own profile
- Upload and manage their own résumés
- Manage their skills
- Manage projects and certifications
- View their career recommendations
- Track their progress
- View notifications

Students must not access another student's private records without authorization.

### 5.2 Faculty

Faculty may:

- View authorized student profiles
- Filter authorized students
- Review student career-readiness information
- Provide permitted feedback

Faculty access must be restricted according to academic program assignments and review permissions.

Faculty members must not automatically receive access to every student in the university.

### 5.3 Administrator

Administrators may:

- Manage authorized user accounts
- Manage faculty access
- Manage academic and career data
- Review permitted audit records
- Manage administrative settings

Administrative endpoints must verify the administrator role on every protected request.

Never rely only on frontend role checks.

### 5.4 Authorization Testing

Test:

- Student accessing another student's profile
- Student accessing faculty endpoints
- Student accessing administrator endpoints
- Faculty accessing unauthorized students
- Faculty attempting administrator actions
- Disabled account attempting authentication
- Expired or revoked token accessing endpoints

Expected result:

Unauthorized access is denied without exposing private information.

---

## 6. Résumé Upload Security and Cloudflare R2

TigerPad accepts résumé uploads.

Supported document formats include:

- PDF
- DOCX

Recommended maximum upload size:

**10 MB**

The actual enforced size limit must be verified in the upload handler.

### 6.1 Required Upload Validation

Validate:

1. File size
2. File extension
3. Actual file content and structure
4. File type
5. Authentication
6. Resource ownership
7. Malware scan result

Do not trust filenames or MIME types supplied by the browser.

Generate safe server-side object names.

Prevent path traversal.

Never execute uploaded files.

### 6.2 Cloudflare R2 Storage Architecture

TigerPad uses Cloudflare R2 as private résumé object storage.

The expected workflow is:

```text
Student
   |
   v
React Frontend
   |
   | Upload résumé
   v
FastAPI Backend
   |
   | Validate file and user
   | Perform required security checks
   v
Cloudflare R2
   |
   | Store private object
   v
MySQL Database
   |
   | Save résumé metadata and ownership
   v
Upload confirmation
```

The backend must ensure that only authorized users can access a résumé.

A résumé's object key should not be treated as sufficient proof of ownership.

### 6.3 R2 Configuration

The backend may require configuration for:

- R2 account endpoint
- Bucket name
- Access key ID
- Secret access key
- Object key prefix
- Upload size limit

The exact variable names must match TigerPad's current storage integration.

### 6.4 R2 Security Requirements

- Keep the résumé bucket private.
- Do not expose R2 secret keys in frontend code.
- Use credentials with only the permissions required.
- Enforce student ownership before uploads, downloads, and deletions.
- Use server-mediated retrieval or short-lived signed URLs where appropriate.
- Avoid logging private résumé contents.
- Validate object keys before accessing storage.
- Apply retention and deletion policies.
- Verify that deleting a résumé removes or invalidates the appropriate database and storage references.

### 6.5 Malware Scanning

Production résumé uploads should be scanned for malware.

The original security guide recommends a scanner such as ClamAV.

If TigerPad uses a hosted scanning provider, its actual implementation and configuration should be documented.

Recommended workflow:

1. Receive upload.
2. Enforce size limit.
3. Validate file structure.
4. Scan for malware.
5. Reject infected or unscannable files when scanning is required.
6. Store the approved document in private R2 storage.
7. Save the corresponding database metadata.
8. Record the upload result.

Setting an environment variable such as `ENABLE_MALWARE_SCANNING=true` does not automatically implement scanning.

The upload handler must explicitly invoke and enforce the scanning service.

### 6.6 Cloudflare R2 Testing

Verify:

- Valid PDF upload succeeds.
- Valid DOCX upload succeeds.
- Unsupported file types are rejected.
- Oversized files are rejected.
- Unauthorized users cannot retrieve another student's résumé.
- Downloaded documents match uploaded documents.
- Deleted documents cannot be accessed afterward.
- Storage failures return safe errors.
- Scanning failures follow the configured security policy.

---

## 7. HTTPS and CORS

Production deployments must use HTTPS.

TigerPad uses Render-hosted HTTPS endpoints for its frontend and backend.

### 7.1 HTTPS Architecture

```text
User Browser
     |
     | HTTPS
     v
Render Frontend
     |
     | HTTPS
     v
Render Backend
     |
     +---- Encrypted Aiven MySQL connection
     |
     +---- HTTPS Cloudflare R2 requests
     |
     +---- HTTPS Groq API requests
```

Render manages the public HTTPS entry points for its hosted services.

A separate Nginx or Caddy installation is not required solely because the application uses FastAPI on Render.

### 7.2 CORS

Only approved frontend origins should be allowed.

Development examples:

```text
http://localhost:3000
http://127.0.0.1:3000
http://localhost:5173
http://127.0.0.1:5173
```

Production frontend origin:

```text
https://tigerpad.onrender.com
```

Avoid wildcard origins in production.

When using cookies across origins, configure credential handling and allowed origins appropriately.

CORS is not an authentication mechanism.

---

## 8. Database Security — Aiven MySQL

TigerPad uses a relational MySQL database hosted by Aiven.

### 8.1 Database Responsibilities

The database stores structured information such as:

- User accounts
- Roles
- Student profiles
- Faculty profiles
- Colleges and departments
- Academic programs
- Skills
- Certifications
- Projects
- Career paths
- Résumé metadata
- Faculty permissions
- Audit records

Cloudflare R2 stores the résumé document objects themselves.

### 8.2 Database Connection

The backend connects to Aiven through the configured MySQL connection settings.

Typical settings include:

- Hostname
- Port
- Database name
- Username
- Password
- TLS/SSL configuration

A SQLAlchemy connection URL may use a format such as:

```text
mysql+pymysql://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
```

This is an example only.

The deployed connection string must match TigerPad's actual driver and configuration.

Use TLS when required by Aiven and verify certificate validation according to the connection driver and hosting configuration.

### 8.3 Database Security Requirements

- Use a dedicated application database account.
- Grant only required permissions.
- Restrict network access where supported.
- Use parameterized SQL or SQLAlchemy queries.
- Avoid constructing SQL from untrusted user input.
- Protect database credentials.
- Enable encrypted connections.
- Maintain protected backups.
- Test backup restoration.

Never use the MySQL root account for routine application connections.

### 8.4 Aiven Service Availability

Aiven database availability is essential to TigerPad's backend startup.

The deployed FastAPI application checks its database connection during startup.

If the MySQL service is powered off or unreachable, the backend may fail to start.

An observed Render startup error was:

```text
TigerPad could not verify the MySQL database connection.

RuntimeError:
TigerPad production startup requires MySQL.
```

This error was encountered while the Aiven MySQL service was powered off.

Restoring the Aiven service is the first recovery action when this condition occurs.

However, similar errors may also result from incorrect credentials, networking failures, or TLS configuration problems.

### 8.5 Aiven Recovery Procedure

If TigerPad's backend fails because MySQL is unavailable:

1. Open the Aiven Console.
2. Select the TigerPad MySQL service.
3. Check whether its status is Powered Off, Rebuilding, or Running.
4. If powered off, use the available service controls to turn it on.
5. Wait until Aiven reports Running.
6. Open the Render dashboard.
7. Select the TigerPad backend service.
8. Restart or redeploy the backend if it has not recovered automatically.
9. Review the latest backend logs.
10. Test the `/status` endpoint.
11. Test login using a dedicated development account.
12. Confirm that student profile information can be retrieved.

Do not delete the database, recreate tables, or change credentials merely because the service was temporarily powered off.

### 8.6 Automatic Power-Off Considerations

Some Aiven service plans may support automatic power-off or inactivity-related suspension.

The team should verify the actual plan behavior and service settings.

For a live demonstration, confirm that Aiven is running before starting the presentation.

For continuous production use, select a hosting configuration that meets the application's availability requirements.

### 8.7 Database Backups

Create and protect database backups.

Example:

```bash
mysqldump -u tigerpad_backup -p \
  --single-transaction \
  tigerpad > tigerpad_backup.sql
```

This example assumes that the backup account has the required permissions and the correct connection settings.

For a remotely hosted Aiven database, the backup command may also require host, port, and TLS parameters.

Protect backup files because they may contain private student information and password hashes.

Do not store unencrypted backups in public folders.

Verify backup restoration periodically.

### 8.8 Database Capacity and Storage

The database's current user count and disk usage should be measured rather than estimated.

Example user count:

```sql
SELECT COUNT(*) AS total_users
FROM users;
```

Example storage measurement:

```sql
SELECT
    table_schema AS database_name,
    ROUND(SUM(data_length) / 1048576, 2) AS data_mb,
    ROUND(SUM(index_length) / 1048576, 2) AS index_mb,
    ROUND(
        SUM(data_length + index_length) / 1048576,
        2
    ) AS total_mb
FROM information_schema.tables
WHERE table_schema = DATABASE()
GROUP BY table_schema;
```

These measurements estimate table and index disk usage.

They do not measure server RAM consumption or establish maximum concurrent-user capacity.

---

## 9. Groq AI Security

TigerPad uses Groq for AI-powered career guidance.

The AI model must be verified against the current production configuration.

### 9.1 AI Scope Restrictions

TigerPad AI should remain focused on:

- Career readiness
- Résumé improvement
- Skills development
- Certifications
- Career paths
- Academic-to-career preparation
- Professional development

Out-of-scope requests should receive appropriate responses.

### 9.2 AI Security Requirements

- Keep `GROQ_API_KEY` on the backend.
- Never expose the key in frontend code.
- Limit user input length.
- Apply AI endpoint rate limiting.
- Handle API timeouts.
- Handle provider failures.
- Treat model output as untrusted.
- Protect private student data.
- Avoid sending unnecessary personal information.
- Do not allow AI responses to bypass authorization.

### 9.3 AI Failure Testing

Test:

- Invalid API key
- Provider timeout
- Rate-limit response
- Network failure
- Empty response
- Unexpected response format
- Malformed résumé
- Out-of-scope question
- Prompt-injection attempts

AI failures must not crash the entire application.

---

## 10. Logging and Audit Records

TigerPad should maintain security and operational logs.

Useful events include:

- Login success
- Login failure
- Account lockout
- Password reset
- User role changes
- Administrator actions
- Faculty access to student records
- Résumé upload failures
- Authorization failures
- Database connection failures
- Cloudflare R2 storage failures

Audit records should include:

- Timestamp
- Acting user ID
- Action type
- Target resource
- Result
- Request identifier, where available

Never log:

- Plaintext passwords
- JWT tokens
- Groq API keys
- Database credentials
- R2 secret keys
- Full résumé contents

Restrict audit-log access to authorized personnel.

Protect logs against unauthorized modification.

Implement log retention according to university requirements.

---

## 11. Monitoring

Production monitoring should detect:

- Application downtime
- Database connection failures
- Aiven service unavailability
- Repeated login failures
- Excessive API requests
- AI provider failures
- R2 upload and download failures
- Storage capacity problems
- Failed backups
- Unexpected server errors

TigerPad provides a backend health endpoint at:

```text
GET /status
```

A basic health response must not expose secrets, database credentials, or sensitive internal details.

A successful HTTP response from `/status` confirms that the backend is responding, but does not necessarily prove that every dependency is healthy.

Use separate authenticated monitoring for sensitive diagnostic information.

---

## 12. Development Startup

Open the existing TigerPad backend folder.

Activate the existing virtual environment.

On macOS or Linux:

```bash
source .venv/bin/activate
```

If the virtual environment uses a different path, use its actual location.

Install dependencies from the existing project dependency file.

For example:

```bash
pip install -r requirements.txt
```

Verify the local environment configuration.

From the TigerPad backend project root, the current application structure supports:

```bash
uvicorn TP_App.main:app --reload
```

Development API documentation is generally available at:

```text
http://127.0.0.1:8000/docs
```

Check the status endpoint:

```text
http://127.0.0.1:8000/status
```

Local development requires valid access to the configured database and any external services used by the requested feature.

---

## 13. Production Deployment — Render, Aiven, and Cloudflare R2

TigerPad uses Render for application hosting, Aiven for relational database hosting, and Cloudflare R2 for private résumé storage.

### 13.1 Render Frontend

The frontend is built using React and Vite.

Its deployment must use the correct backend API base URL.

The deployed frontend is:

```text
https://tigerpad.onrender.com
```

The frontend should communicate with the backend using HTTPS.

### 13.2 Render Backend

The backend uses Python and FastAPI.

Current deployed backend:

```text
https://tigerpad-backend.onrender.com
```

Current startup command:

```bash
uvicorn TP_App.main:app \
  --host 0.0.0.0 \
  --port $PORT \
  --proxy-headers \
  --forwarded-allow-ips="*"
```

The forwarded-header trust configuration must be appropriate for the actual deployment proxy environment.

The backend should run under a managed production process.

Do not use `--reload` in production.

### 13.3 Render Environment Configuration

Before deployment, verify:

- Production mode is enabled.
- Debug mode is disabled.
- Required database configuration is present.
- JWT signing secrets are configured.
- Groq API credentials are configured.
- Cloudflare R2 credentials are configured.
- Allowed frontend origins are restricted.
- File upload limits are enforced.
- Security integrations are correctly configured.

Do not expose environment variable values in screenshots or logs.

### 13.4 Aiven MySQL Deployment

Before starting the backend:

1. Confirm that the Aiven service is running.
2. Verify the database hostname and port.
3. Confirm database credentials.
4. Verify TLS/SSL requirements.
5. Confirm that the approved database schema exists.
6. Verify the backend's database connection.

Do not recreate the database during routine application redeployments.

### 13.5 Cloudflare R2 Deployment

Before enabling résumé uploads:

1. Verify the configured R2 bucket.
2. Confirm that the bucket is private.
3. Verify backend storage credentials.
4. Confirm upload and retrieval permissions.
5. Test a valid document upload.
6. Test an authorized document download.
7. Test unauthorized access denial.
8. Verify database metadata matches stored objects.

### 13.6 Deployment Verification

After deployment:

1. Check Render deployment status.
2. Review backend startup logs.
3. Open the backend `/status` endpoint.
4. Open the frontend website.
5. Test login with a development account.
6. Confirm role-specific dashboard access.
7. Test profile retrieval and saving.
8. Test résumé upload and retrieval.
9. Test AI functionality.
10. Verify database persistence.
11. Review error logs.

### 13.7 Troubleshooting

| Symptom | Possible cause | First check |
|---|---|---|
| Backend fails during startup | MySQL unavailable | Aiven service status |
| MySQL authentication error | Invalid credentials | Render database configuration |
| Database connection timeout | Network or TLS issue | Aiven connectivity settings |
| Frontend loads but login fails | Backend unavailable | Render backend logs |
| Résumé upload fails | R2 credentials, permissions, or validation | Backend logs and R2 settings |
| AI analysis fails | Groq API issue | Backend AI configuration and logs |
| API requests fail in browser | CORS or incorrect API URL | Browser developer tools and Render settings |

Do not disable database checks, authentication, TLS verification, or authorization merely to make a failed deployment start.

---

## 14. Final Testing Checklist

### Student

- [ ] Student can register or sign in.
- [ ] Registration creates the required student profile.
- [ ] Student can access their profile.
- [ ] Student can manage résumés.
- [ ] Student can manage skills.
- [ ] Student can manage projects.
- [ ] Student can manage certifications.
- [ ] Student can view career paths.
- [ ] Student can view progress.
- [ ] Student can view notifications.
- [ ] Student cannot access another student's private information.

### Faculty

- [ ] Faculty can sign in.
- [ ] Faculty can view authorized students.
- [ ] Faculty can filter authorized students.
- [ ] Faculty can submit permitted reviews.
- [ ] Faculty cannot view unauthorized students.
- [ ] Faculty cannot access administrator-only actions.

### Administrator

- [ ] Administrator can sign in.
- [ ] Administrator can manage permitted users.
- [ ] Administrator can manage authorized records.
- [ ] Administrator can access permitted audit logs.
- [ ] Administrator actions are recorded.
- [ ] Unauthorized users cannot access administrator routes.

### Security

- [ ] Passwords are securely hashed.
- [ ] JWT signatures and expiration are validated.
- [ ] Refresh tokens can be revoked.
- [ ] Login rate limiting works.
- [ ] Account lockout works.
- [ ] Invalid file uploads are rejected.
- [ ] Oversized uploads are rejected.
- [ ] Malware scanning is operational.
- [ ] HTTPS is enforced.
- [ ] CORS is restricted.
- [ ] Secrets are protected.
- [ ] SQL injection tests pass.
- [ ] Cross-site scripting protections are tested.
- [ ] Audit logging works.
- [ ] Database backups can be restored.

### Aiven MySQL

- [ ] Aiven service is running.
- [ ] Render backend can connect to MySQL.
- [ ] Database credentials are protected.
- [ ] Database connections use the required encryption.
- [ ] Student data persists after saving.
- [ ] Database connection failures are logged safely.
- [ ] Database recovery procedures are documented.
- [ ] Backup restoration has been tested.

### Cloudflare R2

- [ ] Résumé bucket is private.
- [ ] Backend credentials have appropriate permissions.
- [ ] PDF uploads work.
- [ ] DOCX uploads work.
- [ ] Authorized downloads work.
- [ ] Unauthorized downloads are denied.
- [ ] Résumé metadata matches stored objects.
- [ ] File deletion behavior is verified.
- [ ] Storage errors are handled safely.

### Render

- [ ] Frontend deployment succeeds.
- [ ] Backend deployment succeeds.
- [ ] Backend `/status` responds.
- [ ] Required environment variables are present.
- [ ] Production CORS settings are correct.
- [ ] Render logs do not expose secrets.
- [ ] Backend recovery after Aiven downtime is verified.

### AI

- [ ] Groq connection works.
- [ ] Career guidance works.
- [ ] Out-of-scope requests are handled.
- [ ] AI provider failures are handled.
- [ ] AI rate limits are handled.
- [ ] Prompt-injection attempts are tested.
- [ ] Sensitive information is protected.

---

## 15. Production Readiness

TigerPad should not be considered fully production-ready until all required security controls have been implemented and successfully tested.

Environment variables and documentation alone do not activate security features.

Each feature must be supported by:

1. Application code
2. Infrastructure configuration
3. Appropriate tests
4. Recorded verification results

Before allowing real student accounts, obtain appropriate university approval for deployment, data collection, privacy, and security controls.

Additional operational priorities include:

- Confirming reliable Aiven availability
- Verifying R2 storage access controls
- Testing database backup restoration
- Confirming production authentication security
- Monitoring backend and external-service failures
- Testing performance under expected user load

---

## 16. Final Summary

TigerPad combines React, FastAPI, Aiven MySQL, Cloudflare R2, Render, and Groq AI to support career development at Jackson State University.

The primary security priorities are:

1. Secure authentication
2. Backend role-based authorization
3. Protected student records
4. Safe résumé uploads
5. Private Cloudflare R2 storage
6. Secure Aiven MySQL connections
7. Reliable Render deployment
8. Secure AI integration
9. Audit logging and monitoring
10. Backup and recovery testing

The goal is a reliable, secure, and maintainable career-readiness website for JSU students, faculty, and administrators.

---

## 17. References

1. Digital Frontier. *TigerPad Source Repository*. https://github.com/J00958230/TigerPad
2. Digital Frontier. *TigerPad Deployed Website*. https://tigerpad.onrender.com
3. FastAPI. *FastAPI Documentation*. https://fastapi.tiangolo.com/
4. React. *React Documentation*. https://react.dev/
5. SQLAlchemy. *SQLAlchemy Documentation*. https://docs.sqlalchemy.org/
6. Oracle. *MySQL 8.0 Reference Manual*. https://dev.mysql.com/doc/refman/8.0/en/
7. Aiven. *Aiven Documentation*. https://aiven.io/docs
8. Cloudflare. *R2 Object Storage Documentation*. https://developers.cloudflare.com/r2/
9. Render. *Render Documentation*. https://render.com/docs
10. Groq. *Groq Developer Documentation*. https://console.groq.com/docs
