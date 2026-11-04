
# TigerPad Security and Deployment Guide

**Project:** TigerPad - JSU Career Accelerator
**Institution:** Jackson State University
**Backend:** FastAPI
**Database:** MySQL 8.0
**AI Provider:** Groq
**AI Model:** openai/gpt-oss-20b

---

## 1. Purpose

TigerPad is a university-wide career-readiness website
designed for Jackson State University students, faculty,
and administrators.

The system supports:

- Student career profiles
- Resume management and resume building
- Skills and certifications
- Student projects
- Career-path recommendations
- AI-powered career guidance
- Faculty student review
- Administrator management
- Progress tracking
- Notifications

This guide describes the security requirements,
deployment process, and testing procedures.

This document is a deployment checklist, not proof
that all listed controls have been implemented.

---

## 2. System Architecture

TigerPad uses the following architecture:

Frontend
    |
    | HTTPS
    v
FastAPI Backend
    |
    |----------------------|
    |                      |
    v                      v
MySQL Database         Groq AI API
    |
    v
User Profiles
Resumes
Projects
Skills
Certifications
Career Data
Audit Records

The backend handles authentication, authorization,
data validation, and business logic.

The frontend should never connect directly to MySQL
or expose the Groq API key.

---

## 3. Environment Configuration

TigerPad uses environment variables for configuration.

Important files:

- .env
- .env.example
- config.py
- main.py

The .env file contains actual credentials.

The .env.example file contains safe placeholders.

Never commit the real .env file to Git.

Verify that .gitignore excludes:

.env
.env.*
!.env.example
__pycache__/
*.pyc
.venv/
uploads/
*.log

If sensitive credentials were previously committed,
rotate them immediately.

Use unique secrets for development and production.

---

## 4. Authentication Security

TigerPad supports three user roles:

1. Student
2. Faculty
3. Administrator

### Password Security

Passwords must be stored as secure password hashes.

Recommended algorithms:

- Argon2id
- bcrypt

Never store plaintext passwords.

Never log user passwords.

Use secure password-reset tokens with expiration
and single-use validation.

### JWT Security

JWT authentication must validate:

- Token signature
- Expiration time
- Token type
- User identity
- Account status
- Authorized role

Recommended token settings:

Access token: 30 minutes
Refresh token: 7 days

Refresh tokens should support revocation.

Production refresh tokens should use secure
storage and rotation.

Do not store sensitive authentication tokens
in browser localStorage.

### Account Lockout

Repeated failed login attempts should trigger
temporary protection.

Recommended settings:

Maximum attempts: 5
Lockout duration: 15 minutes

Apply rate limiting to authentication endpoints.

---

## 5. Role-Based Access Control

All protected endpoints must enforce authorization
on the backend.

### Student

Students may:

- Manage their own profile
- Upload and manage their own resumes
- Manage their skills
- Manage projects and certifications
- View their career recommendations
- Track their progress
- View their notifications

Students must not access another student's
private records without authorization.

### Faculty

Faculty may:

- View authorized student profiles
- Filter authorized students
- Review student career-readiness information
- Provide permitted feedback

Faculty must not automatically receive access
to every student in the university.

Faculty authorization must be checked against
the database for each requested student.

### Administrator

Administrators may:

- Manage authorized users
- Manage academic and career data
- Review permitted audit records
- Manage administrative settings

Administrative endpoints must verify the user's
administrator role on every request.

Never rely only on frontend role checks.

### Authorization Testing

Test these cases:

- Student accessing another student's profile
- Student accessing faculty endpoints
- Student accessing administrator endpoints
- Faculty accessing unauthorized students
- Faculty attempting administrator actions
- Disabled account attempting authentication
- Expired or revoked token accessing endpoints

Expected result:

Unauthorized access is denied without exposing
private information.

---

## 6. Resume Upload Security

TigerPad accepts resume uploads.

Supported formats:

- PDF
- DOCX

Recommended maximum upload size:

10 MB

### Required Upload Validation

Validate:

1. File size
2. File extension
3. Actual file content and structure
4. File type
5. Authentication
6. Resource ownership
7. Malware scan result

Do not trust the filename or MIME type supplied
by the browser.

Generate safe server-side filenames.

Prevent path traversal.

Store uploads outside publicly served directories.

Never execute uploaded files.

### Malware Scanning

A production deployment should integrate a
malware-scanning service such as ClamAV.

Recommended workflow:

1. Receive upload.
2. Enforce the size limit.
3. Save to a restricted temporary location.
4. Validate file structure.
5. Scan for malware.
6. Reject infected or unscannable files.
7. Move clean files to protected storage.
8. Record the upload result.

If malware scanning is required, scanning failures
must prevent the file from becoming available.

Setting ENABLE_MALWARE_SCANNING=true does not
automatically install or integrate ClamAV.

The upload handler must explicitly implement scanning.

---

## 7. HTTPS and CORS

Production deployments must use HTTPS.

Recommended deployment:

Internet
    |
    v
HTTPS Reverse Proxy
    |
    v
FastAPI
    |
    v
MySQL

Use a reverse proxy such as Nginx or Caddy.

Configure a valid TLS certificate.

Redirect HTTP traffic to HTTPS.

Do not expose MySQL directly to the public internet.

### CORS

Only approved frontend origins should be allowed.

Development examples:

http://localhost:3000
http://127.0.0.1:3000
http://localhost:5173
http://127.0.0.1:5173

Production must use the actual deployed frontend URL.

Avoid wildcard origins in production.

When using browser cookies across origins,
configure credentials and exact allowed origins
appropriately.

CORS is not an authentication mechanism.

---

## 8. Database Security

TigerPad uses MySQL.

Recommended protections:

- Use a dedicated application database account.
- Grant only required permissions.
- Restrict network access to MySQL.
- Use parameterized SQL or SQLAlchemy queries.
- Avoid constructing SQL from user input.
- Enable TLS where needed.
- Maintain encrypted backups.
- Test backup restoration.

Never use the MySQL root account for routine
application connections.

### Database Backups

Create scheduled database backups.

Example:

mysqldump -u tigerpad_backup -p \
  --single-transaction \
  tigerpad > tigerpad_backup.sql

This example assumes the backup account has the
required permissions.

Protect the resulting file because it may contain
private student information and password hashes.

Do not store unencrypted backups in public folders.

Use encrypted off-site storage and retention policies.

Verify backup restoration periodically.

---

## 9. Groq AI Security

TigerPad uses Groq for AI-powered career guidance.

Configured model:

openai/gpt-oss-20b

### AI Scope Restrictions

TigerPad AI must remain focused on:

- Career readiness
- Resume improvement
- Skills development
- Certifications
- Career paths
- Academic-to-career preparation
- Professional development

Out-of-scope requests should receive an appropriate
response directing the user back to TigerPad topics.

### AI Security Requirements

- Keep GROQ_API_KEY on the backend.
- Never expose the key in frontend code.
- Limit user input length.
- Apply AI endpoint rate limiting.
- Handle API timeouts.
- Handle provider failures.
- Treat model output as untrusted.
- Protect private student data.
- Avoid sending unnecessary personal data.
- Do not allow AI responses to bypass authorization.

### AI Failure Testing

Test:

- Invalid Groq API key
- Provider timeout
- Rate-limit response
- Network failure
- Empty response
- Unexpected response format
- Malformed resume
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
- Resume upload failures
- Authorization failures

Audit records should include:

- Timestamp
- Acting user ID
- Action type
- Target resource
- Result
- Request identifier where available

Never log:

- Plaintext passwords
- JWT tokens
- Groq API keys
- Database credentials
- Full resume contents

Restrict audit-log access to authorized personnel.

Protect logs against unauthorized modification.

Implement log retention according to university
requirements.

---

## 11. Monitoring

Production monitoring should detect:

- Application downtime
- Database connection failures
- Repeated login failures
- Excessive API requests
- AI provider failures
- Storage capacity problems
- Failed backups
- Unexpected server errors

A health endpoint may be provided at:

GET /status

A basic status response should not reveal secrets,
internal database credentials, or sensitive details.

Use separate authenticated monitoring for
sensitive diagnostic information.

---

## 12. Development Startup

Open the existing TigerPad backend folder.

Activate the existing virtual environment.

On macOS or Linux:

source .venv/bin/activate

If the virtual environment has a different name,
use its actual path.

Install dependencies using the project's
existing dependency file.

For example, if requirements.txt exists:

pip install -r requirements.txt

Verify that the .env configuration is valid.

Start FastAPI using the existing application entry point.

If main.py is inside the current directory:

uvicorn main:app --reload

If the project uses backend/main.py and the
backend directory is a Python package, the
appropriate module path may be:

uvicorn backend.main:app --reload

Use the command matching the actual project structure.

Development documentation is usually available at:

http://127.0.0.1:8000/docs

Check:

http://127.0.0.1:8000/status

The actual status path must match main.py.

---

## 13. Production Deployment

### Step 1: Prepare the Server

Use a maintained operating system.

Install:

- Python
- MySQL client dependencies
- Required Python packages
- Reverse proxy
- TLS certificate tooling
- Malware scanner, if enabled
- Monitoring and backup tools

### Step 2: Configure Environment

Set:

APP_ENV=production
DEBUG=false
FORCE_HTTPS=true

Replace all development secrets.

Restrict CORS to the deployed frontend.

Verify that all required environment variables
are actually read by config.py.

### Step 3: Prepare MySQL

Create the production database.

Apply the approved schema and migrations.

Create a dedicated database user.

Load only appropriate seed data.

Do not copy real student data into test systems.

### Step 4: Configure Upload Storage

Create protected directories.

Example:

uploads/resumes/
uploads/temporary/

Set restrictive filesystem permissions.

Ensure only the application service account
can access protected uploads.

Configure malware scanning.

### Step 5: Run FastAPI

Use a managed production process.

For example, with a suitable ASGI deployment:

uvicorn main:app --host 127.0.0.1 --port 8000

Use the correct module path for the deployment.

Run under a dedicated non-root service account.

Configure automatic restarts and logging.

Do not use --reload in production.

### Step 6: Configure HTTPS

Configure Nginx or Caddy.

Forward HTTPS requests to FastAPI.

Use trusted proxy-header settings only when the
proxy configuration is correct.

Enable HTTP-to-HTTPS redirection.

### Step 7: Validate Security

Verify:

- HTTPS
- CORS
- JWT validation
- Role authorization
- Resume upload validation
- Malware scanning
- Database access restrictions
- Audit logging
- Backups
- Monitoring

---

## 14. Final Testing Checklist

### Student

- [ ] Student can register or sign in.
- [ ] Student can access their profile.
- [ ] Student can manage resumes.
- [ ] Student can manage skills.
- [ ] Student can manage projects.
- [ ] Student can manage certifications.
- [ ] Student can view career paths.
- [ ] Student can view progress.
- [ ] Student can view notifications.
- [ ] Student cannot access private data of others.

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
- [ ] Unauthorized users cannot access admin routes.

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

TigerPad should not be considered production-ready
until all required security controls are implemented
and successfully tested.

Environment variables and documentation alone do
not activate security features.

Each feature must be supported by application code,
infrastructure configuration, and appropriate tests.

Before allowing real student accounts, obtain
appropriate university approval for deployment,
data collection, privacy, and security controls.

---

## 16. Final Summary

TigerPad combines FastAPI, MySQL, and Groq AI to
support student career development at Jackson State
University.

The primary security priorities are:

1. Secure authentication
2. Backend role-based authorization
3. Protected student records
4. Safe resume uploads
5. Secure AI integration
6. HTTPS and database security
7. Audit logging and monitoring
8. Reliable backup and recovery

The goal is a reliable, secure, and maintainable
career-readiness website for JSU students,
faculty, and administrators.
