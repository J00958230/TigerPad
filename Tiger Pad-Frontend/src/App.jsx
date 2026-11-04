/*
 * TIGERPAD — MAIN FRONTEND APPLICATION (App.jsx)
 * ------------------------------------------------------------
 * Overall function:
 * This file powers the TigerPad website for Jackson State University
 * students, faculty reviewers, and administrators. It connects the
 * React interface to TigerPad's FastAPI backend.
 *
 * Main responsibilities:
 * 1. Handle the application's authenticated navigation and role-based
 *    student, faculty, and administrator views.
 * 2. Display student profiles, academic programs, skills, projects,
 *    certifications, career goals, and other career-readiness records.
 * 3. Provide the redesigned Student Resume Studio: library, builder,
 *    document preview, and AI review. Upload/list resumes,
 *    show the original uploaded resume, request analysis, display
 *    scores and feedback, and preview a suggested resume draft.
 * 4. Display career guidance, readiness results, progress,
 *    notifications, and other available TigerPad features.
 * 5. Call protected backend endpoints through the shared API helpers.
 *
 * Resume workflow:
 * - The selected-résumé summary remains visible above all Studio tabs.
 * - Students may remove old résumés from the active library with confirmation.
 * - Uploaded originals remain separate from suggested drafts.
 * - Resume analysis evaluates the student's existing resume.
 * - Suggested drafts use information from the student's saved profile.
 * - A suggested draft should never be presented as a verified fact
 *   unless the underlying student record supports it.
 *
 * Configuration and maintenance:
 * - VITE_API_BASE_URL controls the backend API URL when configured.
 * - Existing App.css class names are retained to preserve styling.
 * - Keep role restrictions, authorization, and error handling intact.
 * - When editing this file, preserve these explanatory comments.
 */

import { useEffect, useRef, useState } from "react";
import "./App.css";

// The Vite environment can override this value for another developer's machine.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const HEALTH_URL = API_BASE_URL.replace(/\/api\/?$/, "") + "/health";
const COOKIE_AUTH_ENABLED =
  import.meta.env.VITE_COOKIE_AUTH_ENABLED === "true";

// Shared form styles keep new screens consistent with the existing design.
const selectStyle = {
  width: "100%",
  padding: "13px 14px",
  border: "1px solid #dce3ee",
  borderRadius: "11px",
  background: "white",
};

const textareaStyle = {
  width: "100%",
  padding: "13px 14px",
  border: "1px solid #dce3ee",
  borderRadius: "11px",
  resize: "vertical",
};

const EMPTY_PROFILE = {
  preferred_name: "",
  academic_level: "",
  expected_graduation_date: "",
  gpa: "",
  professional_headline: "",
  bio: "",
  linkedin_url: "",
  portfolio_url: "",
  profile_visibility: "private",
};

// Convert API responses that may be arrays, wrapped arrays, or single objects.
function asArray(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.items)) return value.items;
  return value ? [value] : [];
}

// Display enum values in a readable way.
function displayLabel(value, fallback = "") {
  if (!value) return fallback;
  return String(value)
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

// Keep decimal score formatting consistent across the application.
function displayScore(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(2) : String(value);
}

// Extract a useful FastAPI/Pydantic error message.
function errorMessage(payload) {
  if (Array.isArray(payload?.detail)) {
    return payload.detail
      .map((item) => item.msg || "Validation error")
      .join(" ");
  }
  return payload?.detail || payload?.message || "TigerPad request failed.";
}

function token() {
  return sessionStorage.getItem("tigerpad_access_token");
}

function refreshToken() {
  return sessionStorage.getItem("tigerpad_refresh_token");
}

// Save tokens returned by login or refresh endpoints.
function saveTokens(payload) {
  const tokens = payload?.tokens || payload;
  if (COOKIE_AUTH_ENABLED) {
    sessionStorage.removeItem("tigerpad_access_token");
    sessionStorage.removeItem("tigerpad_refresh_token");
    return tokens;
  }
  if (tokens?.access_token) {
    sessionStorage.setItem("tigerpad_access_token", tokens.access_token);
  }
  if (tokens?.refresh_token) {
    sessionStorage.setItem("tigerpad_refresh_token", tokens.refresh_token);
  }
  return tokens;
}

// Central JSON request helper. It adds the bearer token and attempts one
// refresh when the access token expires.
async function apiRequest(path, options = {}, allowRefresh = true) {
  const headers = {
    Accept: "application/json",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
  };

  const accessToken = token();
  if (accessToken) headers.Authorization = "Bearer " + accessToken;

  const response = await fetch(API_BASE_URL + path, {
    ...options,
    credentials: COOKIE_AUTH_ENABLED ? "include" : "same-origin",
    headers,
  });

  if (
    response.status === 401 &&
    allowRefresh &&
    (refreshToken() || COOKIE_AUTH_ENABLED)
  ) {
    try {
      const refreshResponse = await fetch(API_BASE_URL + "/auth/refresh", {
        method: "POST",
        credentials: COOKIE_AUTH_ENABLED ? "include" : "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        ...(refreshToken()
          ? { body: JSON.stringify({ refresh_token: refreshToken() }) }
          : {}),
      });

      const refreshPayload = await refreshResponse.json().catch(() => ({}));

      if (refreshResponse.ok) {
        saveTokens(refreshPayload);
        return apiRequest(path, options, false);
      }
    } catch {
      // The original authentication error is returned below.
    }
  }

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(errorMessage(payload));
    error.status = response.status;
    throw error;
  }

  return payload;
}

// Multipart upload helper. JSON content headers must not be set for FormData.
async function uploadRequest(path, formData) {
  const headers = { Accept: "application/json" };
  const accessToken = token();

  if (accessToken) {
    headers.Authorization = "Bearer " + accessToken;
  }

  const response = await fetch(API_BASE_URL + path, {
    method: "POST",
    credentials: COOKIE_AUTH_ENABLED ? "include" : "same-origin",
    headers,
    body: formData,
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(errorMessage(payload));
    error.status = response.status;
    throw error;
  }

  return payload;
}

// Binary helper used by the PDF preview route.
async function _blobRequest(path) {
  const response = await fetch(API_BASE_URL + path, {
    credentials: COOKIE_AUTH_ENABLED ? "include" : "same-origin",
    headers: token()
      ? { Authorization: "Bearer " + token() }
      : {},
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(errorMessage(payload));
  }

  return response.blob();
}

function Notice({ notice }) {
  if (!notice) return null;
  return <div className={"notice notice-" + notice.type}>{notice.text}</div>;
}

function HealthPill({ healthStatus }) {
  return (
    <div className="health-pill">
      <span className={"status-dot status-" + healthStatus} />
      Backend{" "}
      {healthStatus === "online"
        ? "online"
        : healthStatus === "checking"
          ? "checking"
          : "unavailable"}
    </div>
  );
}

function PageHeader({ onBack, actions = null }) {
  return (
    <header className="dashboard-header">
      <div className="dashboard-brand">
        <div className="brand-mark brand-mark-small">TP</div>
        <span>TigerPad</span>
      </div>

      {actions || (
        <button type="button" className="logout-button" onClick={onBack}>
          ← Dashboard
        </button>
      )}
    </header>
  );
}

// Authentication screen used for both registration and login.
function AuthView({ healthStatus, onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState(null);

  const [form, setForm] = useState({
    jsu_email: "",
    password: "",
    confirm_password: "",
    first_name: "",
    last_name: "",
  });

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setNotice(null);

    setForm({
      jsu_email: "",
      password: "",
      confirm_password: "",
      first_name: "",
      last_name: "",
    });
  }

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setNotice(null);

    try {
      if (mode === "register") {
        await apiRequest("/auth/register", {
          method: "POST",
          body: JSON.stringify(form),
        });

        setMode("login");
        setForm((current) => ({
          ...current,
          password: "",
          confirm_password: "",
        }));

        setNotice({
          type: "success",
          text: "Registration successful. Sign in to continue.",
        });

        return;
      }

      const result = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          jsu_email: form.jsu_email,
          password: form.password,
        }),
      });

      saveTokens(result);

      const currentUser = await apiRequest("/auth/me");
      onAuthenticated(currentUser);
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="brand-panel">
        <div className="brand-mark">TP</div>

        <p className="eyebrow">Jackson State University</p>

        <h1>
          Your path.
          <br />
          Your potential.
        </h1>

        <p className="brand-copy">
          TigerPad connects education, skills, experiences, and goals to
          meaningful career directions for every JSU major.
        </p>

        <div className="brand-points">
          <span>Explore career paths</span>
          <span>Build your professional profile</span>
          <span>Track your readiness</span>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-heading">
            <span className="mini-label">TigerPad</span>

            <h2>
              {mode === "login" ? "Welcome back" : "Create your account"}
            </h2>

            <p>
              {mode === "login"
                ? "Sign in to continue your career-readiness journey."
                : "Start building your personalized career-readiness profile."}
            </p>
          </div>

          <Notice notice={notice} />

          <form onSubmit={submit} className="auth-form">
            {mode === "register" && (
              <div className="form-row">
                <label>
                  First name
                  <input
                    name="first_name"
                    value={form.first_name}
                    onChange={updateField}
                    required
                  />
                </label>

                <label>
                  Last name
                  <input
                    name="last_name"
                    value={form.last_name}
                    onChange={updateField}
                    required
                  />
                </label>
              </div>
            )}

            <label>
              JSU email
              <input
                name="jsu_email"
                type="email"
                value={form.jsu_email}
                onChange={updateField}
                placeholder="you@jsums.edu"
                required
              />
            </label>

            <label>
              Password
              <input
                name="password"
                type="password"
                value={form.password}
                onChange={updateField}
                required
              />
            </label>

            {mode === "register" && (
              <label>
                Confirm password
                <input
                  name="confirm_password"
                  type="password"
                  value={form.confirm_password}
                  onChange={updateField}
                  required
                />
              </label>
            )}

            <button className="primary-button" type="submit" disabled={loading}>
              {loading
                ? "Please wait..."
                : mode === "login"
                  ? "Sign in to TigerPad"
                  : "Create TigerPad account"}
            </button>
          </form>

          <div className="mode-switch">
            <span>
              {mode === "login"
                ? "Need a TigerPad account?"
                : "Already have an account?"}
            </span>

            <button
              type="button"
              className="text-button"
              onClick={() =>
                switchMode(mode === "login" ? "register" : "login")
              }
            >
              {mode === "login" ? "Create one" : "Sign in"}
            </button>
          </div>

          <div className="service-status">
            <span className={"status-dot status-" + healthStatus} />
            Backend:{" "}
            {healthStatus === "online"
              ? "online"
              : healthStatus === "checking"
                ? "checking"
                : "unavailable"}
          </div>
        </div>
      </section>
    </main>
  );
}

// Main authenticated shell.
function AuthenticatedApp({ user, healthStatus, onLogout }) {
  const [view, setView] = useState("dashboard");
  const [unreadCount, setUnreadCount] = useState(0);
  const [notificationRefresh, setNotificationRefresh] = useState(0);

  // Normalize the database/JWT role.
  const normalizedRole = String(user.role || "student").toLowerCase();

  const isFaculty = normalizedRole === "faculty";
  const isAdmin =
    normalizedRole === "admin" || normalizedRole === "administrator";

  // Refresh the student-only bell count when the page changes or an alert is updated.
  useEffect(() => {
    if (isFaculty || isAdmin) return;
    let active = true;
    apiRequest("/students/me/notifications/unread-count")
      .then((data) => {
        if (active) setUnreadCount(Number(data.unread_count) || 0);
      })
      .catch(() => {
        if (active) setUnreadCount(0);
      });
    return () => { active = false; };
  }, [view, notificationRefresh, isFaculty, isAdmin]);

  const openNotifications = () => setView("notifications");
  const refreshNotifications = () =>
    setNotificationRefresh((current) => current + 1);

  const studentNavigation = [
    ["dashboard", "Dashboard"],
    ["profile", "My profile"],
    ["careers", "Career paths"],
    ["resume", "Résumé"],
    ["readiness", "Readiness"],
    ["interviews", "Interviews"],
    ["activity", "Progress"],
    ["notifications", "Notifications"],
    ["resources", "Resources"],
  ];

  const facultyNavigation = [
    ["dashboard", "Dashboard"],
    ["careers", "Career paths"],
    ["resources", "Resources"],
    ["faculty-profile", "Faculty Profile"],
    ["faculty", "Student Reviews"],
  ];

  // Administrator tools live on Dashboard; avoid a duplicate Admin tab.
  const adminNavigation = [
    ["dashboard", "Dashboard"],
    ["careers", "Career paths"],
    ["manage-careers", "Manage Career Paths"],
    ["manage-users", "Manage Users"],
    ["audit-logs", "Audit Logs"],
    ["resources", "Resources"],
  ];

  const navigation = isFaculty
    ? facultyNavigation
    : isAdmin
      ? adminNavigation
      : studentNavigation;

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <div className="dashboard-brand">
          <div className="brand-mark brand-mark-small">TP</div>
          <span>TigerPad</span>
        </div>

        <div className="header-actions">
          {!isFaculty && !isAdmin && (
            <button
              type="button"
              className="secondary-button"
              onClick={openNotifications}
              aria-label={`Notifications, ${unreadCount} unread`}
              title="Student notifications"
              style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
            >
              <span aria-hidden="true">🔔</span>
              Notifications
              {unreadCount > 0 && (
                <strong style={{ borderRadius: 12, padding: "2px 7px", background: "#7b1830", color: "white" }}>
                  {unreadCount > 99 ? "99+" : unreadCount}
                </strong>
              )}
            </button>
          )}
          <span className="student-role">
            {displayLabel(user.role, "student")}
          </span>

          <button
            type="button"
            className="logout-button"
            onClick={onLogout}
          >
            Sign out
          </button>
        </div>
      </header>

      <section className="dashboard-content">
        {view === "dashboard" && isFaculty && (
          <FacultyDashboardView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
            onOpen={setView}
            navigation={navigation}
            showPageHeader={false}
          />
        )}

        {view === "dashboard" && isAdmin && (
          <AdminView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
            onOpen={setView}
            navigation={navigation}
            showPageHeader={false}
          />
        )}

        {view === "dashboard" && !isFaculty && !isAdmin && (
          <DashboardView
            unreadCount={unreadCount}
            user={user}
            healthStatus={healthStatus}
            onOpen={setView}
            navigation={navigation}
          />
        )}

        {view === "profile" && (
          <ProfileWorkspaceView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
          />
        )}

        {view === "careers" && (
          <CareerPathsView
            isStudent={!isFaculty && !isAdmin}
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
          />
        )}

        {view === "manage-users" && isAdmin && (
          <AdminUserManagementView
            healthStatus={healthStatus}
            onOpen={setView}
            navigation={navigation}
            currentUser={user}
          />
        )}

        {view === "audit-logs" && isAdmin && (
          <AdminAuditLogsView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
            onOpen={setView}
            navigation={navigation}
          />
        )}

        {view === "manage-careers" && isAdmin && (
          <>
            <PageHeader onBack={() => setView("dashboard")} />
            <div className="welcome-row">
              <div>
                <p className="eyebrow">Administrator tools</p>
                <h1>Manage career paths.</h1>
                <p className="dashboard-intro">
                  Create drafts, edit career paths, and control publication.
                </p>
              </div>
              <HealthPill healthStatus={healthStatus} />
            </div>
            <AdminCareerPathManager />
          </>
        )}

        {view === "resume" && (
          <ResumeView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
          />
        )}

        {view === "readiness" && (
          <ReadinessView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
            onOpen={setView}
          />
        )}

        {view === "interviews" && (
          <InterviewsView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
          />
        )}

        {view === "notifications" && !isFaculty && !isAdmin && (
          <StudentNotificationsView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
            onUpdated={refreshNotifications}
          />
        )}

        {view === "activity" && (
          <ActivityView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
          />
        )}

        {view === "resources" && (
          <ResourcesView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
          />
        )}

        {view === "faculty-profile" && isFaculty && (
          <FacultyProfileView
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
          />
        )}

        {view === "faculty" && isFaculty && (
          <FacultyView
            facultyUserId={user.user_id}
            healthStatus={healthStatus}
            onBack={() => setView("dashboard")}
            onOpen={setView}
            navigation={navigation}
          />
        )}


      </section>
    </main>
  );
}

// Quick tabs stay in one horizontal row.
function QuickTabs({ navigation, onOpen }) {
  return (
    <nav className="quick-tabs" aria-label="TigerPad quick navigation">
      {navigation.map(([key, label]) => (
        <button
          type="button"
          key={key}
          className="quick-tab text-button"
          onClick={() => onOpen(key)}
        >
          {label}
        </button>
      ))}
    </nav>
  );
}

// Student dashboard.
function DashboardView({ user, healthStatus, onOpen, navigation, unreadCount }) {
  const [summary, setSummary] = useState(null);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    apiRequest("/students/me/profile/summary")
      .then(setSummary)
      .catch((error) =>
        setNotice({ type: "error", text: error.message }),
      );
  }, []);

  const complete = Boolean(summary?.is_profile_complete);
  const firstName =
    summary?.preferred_name || user.first_name || "Student";

  const academicLevel = displayLabel(
    summary?.academic_level,
    "Academic level not added",
  );

  return (
    <>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">Student dashboard</p>
          <h1>Welcome, {firstName}.</h1>
          <p className="dashboard-intro">
            Your TigerPad career-readiness workspace starts here.
          </p>
        </div>

        <HealthPill healthStatus={healthStatus} />
      </div>

      <Notice notice={notice} />

      <QuickTabs navigation={navigation} onOpen={onOpen} />

      {unreadCount > 0 && (
        <article className="dashboard-card" style={{ marginTop: 20 }}>
          <p className="card-label">New activity</p>
          <h2>You have {unreadCount} unread notification{unreadCount === 1 ? "" : "s"}.</h2>
          <button type="button" className="secondary-button" onClick={() => onOpen("notifications")}>
            View notifications
          </button>
        </article>
      )}

      <div className="dashboard-grid">
        {complete ? (
          <article className="dashboard-card dashboard-card-primary">
            <p className="card-label">Keep building</p>
            <h2>Explore your career direction</h2>
            <p>
              Your profile is complete. Explore career paths and review your
              readiness.
            </p>
            <button
              type="button"
              className="secondary-button"
              onClick={() => onOpen("careers")}
            >
              Explore career paths
            </button>
          </article>
        ) : (
          <article className="dashboard-card dashboard-card-primary">
            <p className="card-label">Your next step</p>
            <h2>Complete your student profile</h2>
            <p>
              Add academic information, skills, experiences, and goals so
              TigerPad can personalize guidance.
            </p>
            <button
              type="button"
              className="secondary-button"
              onClick={() => onOpen("profile")}
            >
              Build my profile
            </button>
          </article>
        )}

        <article className="dashboard-card score-card">
          <p className="card-label">Your profile</p>
          <strong>{complete ? "Complete" : "In progress"}</strong>
          <p>
            {summary?.professional_headline ||
              "Complete your profile to personalize TigerPad."}
          </p>
          <p>{academicLevel}</p>
          <button
            type="button"
            className="text-button"
            onClick={() => onOpen("profile")}
          >
            Edit profile
          </button>
        </article>
      </div>

      <section className="feature-section">
        <div>
          <p className="eyebrow">Explore TigerPad</p>
          <h2>Tools for every JSU major</h2>
        </div>

        <div className="feature-grid">
          {[
            ["careers", "Career paths", "Explore generalized career directions."],
            ["readiness", "Readiness", "Understand strengths and skill gaps."],
            ["resume", "Résumé workspace", "Create, upload, and improve résumés."],
            ["interviews", "Interview practice", "Practice general behavioral questions."],
          ].map(([key, title, text]) => (
            <article className="feature-card" key={key}>
              <span className="feature-number">→</span>
              <h3>{title}</h3>
              <p>{text}</p>
              <button
                type="button"
                className="text-button"
                onClick={() => onOpen(key)}
              >
                Open →
              </button>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

// Generic API-backed collection form.
function RecordSection({
  title,
  description,
  path,
  idField,
  fields,
  records,
  setRecords,
  formatRecord,
}) {
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(null);

  function updateField(event) {
    const { name, value, type, checked } = event.target;

    setForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);

    try {
      const payload = {};

      fields.forEach((field) => {
        let value = form[field.name];

        if (field.type === "number") {
          value =
            value === "" || value === undefined
              ? null
              : Number(value);
        }

        if (field.type === "checkbox") {
          value = Boolean(value);
        }

        if (value === "") {
          value = null;
        }

        payload[field.name] = value;
      });

      const saved = await apiRequest(path, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setRecords((current) => [...current, saved]);
      setForm({});
      setNotice({ type: "success", text: title + " saved." });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setSaving(false);
    }
  }

  async function remove(record) {
    if (
      !window.confirm(
        "Remove this " + title.toLowerCase() + "?",
      )
    ) {
      return;
    }

    try {
      await apiRequest(path + "/" + record[idField], {
        method: "DELETE",
      });

      setRecords((current) =>
        current.filter((item) => item[idField] !== record[idField]),
      );
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    }
  }

  return (
    <article
      className="dashboard-card"
      style={{ marginTop: "24px" }}
    >
      <p className="card-label">{title}</p>
      <h2>{title}</h2>
      <p>{description}</p>

      <Notice notice={notice} />

      <form onSubmit={submit} className="auth-form">
        <div className="form-row">
          {fields.map((field) => (
            <label key={field.name}>
              {field.label}

              {field.type === "textarea" ? (
                <textarea
                  name={field.name}
                  value={form[field.name] || ""}
                  onChange={updateField}
                  rows="3"
                  style={textareaStyle}
                  required={field.required}
                />
              ) : field.type === "select" ? (
                <select
                  name={field.name}
                  value={form[field.name] || ""}
                  onChange={updateField}
                  style={selectStyle}
                  required={field.required}
                >
                  <option value="">Select</option>

                  {(field.options || []).map((option) => (
                    <option
                      key={option.value}
                      value={option.value}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : field.type === "checkbox" ? (
                <input
                  name={field.name}
                  type="checkbox"
                  checked={Boolean(form[field.name])}
                  onChange={updateField}
                />
              ) : (
                <input
                  name={field.name}
                  type={field.type || "text"}
                  value={form[field.name] || ""}
                  onChange={updateField}
                  placeholder={field.placeholder || ""}
                  required={field.required}
                />
              )}
            </label>
          ))}
        </div>

        <button
          type="submit"
          className="secondary-button"
          disabled={saving}
        >
          {saving ? "Saving..." : "Add " + title}
        </button>
      </form>

      <div style={{ marginTop: "18px" }}>
        {records.length === 0 ? (
          <p>No records added yet.</p>
        ) : (
          records.map((record) => (
            <div
              key={record[idField]}
              style={{
                borderTop: "1px solid #dce3ee",
                padding: "12px 0",
              }}
            >
              <strong>{formatRecord(record)}</strong>

              <button
                type="button"
                className="text-button"
                onClick={() => remove(record)}
                style={{ float: "right" }}
              >
                Remove
              </button>
            </div>
          ))
        )}
      </div>
    </article>
  );
}

// Profile workspace.
// Fetch the full approved catalog so saved IDs display real names, not placeholders.
async function loadTigerPadCatalog(endpoint) {
  const items = [];
  const pageSize = 50;
  for (let offset = 0; offset <= 10000; offset += pageSize) {
    const separator = endpoint.includes("?") ? "&" : "?";
    const page = asArray(await apiRequest(`${endpoint}${separator}limit=${pageSize}&offset=${offset}`));
    items.push(...page);
    if (page.length < pageSize) break;
  }
  return items;
}

function ProfileWorkspaceView({ healthStatus, onBack }) {
  const [profile, setProfile] = useState(EMPTY_PROFILE);
  const [profileExists, setProfileExists] = useState(false);

  const [catalogs, setCatalogs] = useState({
    programs: [],
    skills: [],
    paths: [],
  });

  const [records, setRecords] = useState({
    programs: [],
    skills: [],
    goals: [],
    experiences: [],
    projects: [],
    certifications: [],
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    let cancelled = false;

    Promise.allSettled([
      apiRequest("/students/me/profile"),
      loadTigerPadCatalog("/academic-programs"),
      loadTigerPadCatalog("/skills"),
      loadTigerPadCatalog("/career-paths"),
      apiRequest("/students/me/programs"),
      apiRequest("/students/me/skills"),
      apiRequest("/students/me/career-goals"),
      apiRequest("/students/me/experiences"),
      apiRequest("/students/me/projects"),
      apiRequest("/students/me/certifications"),
    ]).then((results) => {
      if (cancelled) return;

      const value = (index, fallback) =>
        results[index].status === "fulfilled"
          ? results[index].value
          : fallback;

      const loadedProfile = value(0, null);

      if (loadedProfile) {
        setProfile({
          ...EMPTY_PROFILE,
          ...loadedProfile,
          gpa: loadedProfile.gpa ?? "",
        });
        setProfileExists(true);
      }

      setCatalogs({
        programs: asArray(value(1, [])),
        skills: asArray(value(2, [])),
        paths: asArray(value(3, [])),
      });

      setRecords({
        programs: asArray(value(4, [])),
        skills: asArray(value(5, [])),
        goals: asArray(value(6, [])),
        experiences: asArray(value(7, [])),
        projects: asArray(value(8, [])),
        certifications: asArray(value(9, [])),
      });
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  function updateProfile(event) {
    const { name, value } = event.target;

    setProfile((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function saveProfile(event) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);

    try {
      const saved = await apiRequest("/students/me/profile", {
        method: profileExists ? "PATCH" : "POST",
        body: JSON.stringify({
          preferred_name: profile.preferred_name || null,
          academic_level: profile.academic_level || null,
          expected_graduation_date:
            profile.expected_graduation_date || null,
          gpa: profile.gpa === "" ? null : Number(profile.gpa),
          professional_headline:
            profile.professional_headline || null,
          bio: profile.bio || null,
          linkedin_url: profile.linkedin_url || null,
          portfolio_url: profile.portfolio_url || null,
          profile_visibility:
            profile.profile_visibility || "private",
        }),
      });

      setProfile({
        ...EMPTY_PROFILE,
        ...saved,
        gpa: saved.gpa ?? "",
      });

      setProfileExists(true);

      setNotice({
        type: "success",
        text: "Your profile was saved.",
      });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setSaving(false);
    }
  }

  const programOptions = catalogs.programs.map((item) => ({
    value: item.program_id,
    label: item.name,
  }));

  const skillOptions = catalogs.skills.map((item) => ({
    value: item.skill_id,
    label: item.name,
  }));

  const pathOptions = catalogs.paths.map((item) => ({
    value: item.career_path_id,
    label: item.name,
  }));

  if (loading) {
    return (
      <article className="dashboard-card">
        <p>Loading your profile workspace...</p>
      </article>
    );
  }

  return (
    <>
      <PageHeader onBack={onBack} />

      <div className="welcome-row">
        <div>
          <p className="eyebrow">Student profile</p>
          <h1>Build your profile.</h1>
          <p className="dashboard-intro">
            Your profile powers readiness, career matching, and
            recommendations.
          </p>
        </div>

        <HealthPill healthStatus={healthStatus} />
      </div>

      <Notice notice={notice} />

      <article
        className="dashboard-card"
        style={{ marginTop: "24px" }}
      >
        <p className="card-label">Basic information</p>

        <form onSubmit={saveProfile} className="auth-form">
          <div className="form-row">
            <label>
              Preferred name
              <input
                name="preferred_name"
                value={profile.preferred_name}
                onChange={updateProfile}
              />
            </label>

            <label>
              Academic level
              <select
                name="academic_level"
                value={profile.academic_level}
                onChange={updateProfile}
                style={selectStyle}
              >
                <option value="">Select level</option>
                <option value="freshman">Freshman</option>
                <option value="sophomore">Sophomore</option>
                <option value="junior">Junior</option>
                <option value="senior">Senior</option>
                <option value="graduate">Graduate</option>
              </select>
            </label>
          </div>

          <div className="form-row">
            <label>
              Expected graduation date
              <input
                name="expected_graduation_date"
                type="date"
                value={profile.expected_graduation_date}
                onChange={updateProfile}
              />
            </label>

            <label>
              GPA
              <input
                name="gpa"
                type="number"
                min="0"
                max="4"
                step="0.01"
                value={profile.gpa}
                onChange={updateProfile}
              />
            </label>
          </div>

          <label>
            Professional headline
            <input
              name="professional_headline"
              value={profile.professional_headline}
              onChange={updateProfile}
            />
          </label>

          <label>
            Bio
            <textarea
              name="bio"
              value={profile.bio}
              onChange={updateProfile}
              rows="4"
              style={textareaStyle}
            />
          </label>

          <div className="form-row">
            <label>
              LinkedIn URL
              <input
                name="linkedin_url"
                type="url"
                value={profile.linkedin_url}
                onChange={updateProfile}
              />
            </label>

            <label>
              Portfolio URL
              <input
                name="portfolio_url"
                type="url"
                value={profile.portfolio_url}
                onChange={updateProfile}
              />
            </label>
          </div>

          <label>
            Profile visibility
            <select
              name="profile_visibility"
              value={profile.profile_visibility}
              onChange={updateProfile}
              style={selectStyle}
            >
              <option value="private">Private</option>
              <option value="campus">JSU campus</option>
              <option value="public">Public</option>
            </select>
          </label>

          <button
            className="primary-button"
            type="submit"
            disabled={saving}
          >
            {saving ? "Saving profile..." : "Save profile"}
          </button>
        </form>
      </article>

      <RecordSection
        title="Academic program"
        description="Connect your major or academic program."
        path="/students/me/programs"
        idField="student_program_id"
        records={records.programs}
        setRecords={(value) =>
          setRecords((current) => ({
            ...current,
            programs:
              typeof value === "function"
                ? value(current.programs)
                : value,
          }))
        }
        fields={[
          {
            name: "program_id",
            label: "Program",
            type: "select",
            options: programOptions,
            required: true,
          },
          {
            name: "status",
            label: "Status",
            type: "select",
            options: [
              { value: "active", label: "Active" },
              { value: "completed", label: "Completed" },
            ],
          },
          {
            name: "is_primary",
            label: "Primary program",
            type: "checkbox",
          },
        ]}
        formatRecord={(item) => {
          const academicProgram = catalogs.programs.find(
            (program) => Number(program.program_id) === Number(item.program_id)
          );
          return (
            (academicProgram?.name || item.program_name || `Program #${item.program_id}`) +
            " · " +
            displayLabel(item.status, "Active") +
            (item.is_primary ? " · Primary program" : "")
          );
        }}
      />

      <RecordSection
        title="Skill"
        description="Add skills and evidence for your readiness score."
        path="/students/me/skills"
        idField="student_skill_id"
        records={records.skills}
        setRecords={(value) =>
          setRecords((current) => ({
            ...current,
            skills:
              typeof value === "function"
                ? value(current.skills)
                : value,
          }))
        }
        fields={[
          {
            name: "skill_id",
            label: "Skill",
            type: "select",
            options: skillOptions,
            required: true,
          },
          {
            name: "proficiency_level",
            label: "Proficiency (1–5)",
            type: "number",
            required: true,
          },
          {
            name: "years_experience",
            label: "Years",
            type: "number",
          },
          {
            name: "evidence_description",
            label: "Evidence",
            type: "textarea",
          },
        ]}
        formatRecord={(item) => {
          const skill = catalogs.skills.find(
            (entry) => Number(entry.skill_id) === Number(item.skill_id)
          );
          return (skill?.name || item.skill_name || `Skill #${item.skill_id}`) +
            " · proficiency " + item.proficiency_level;
        }}
      />

      <RecordSection
        title="Career goal"
        description="Track a career direction you want to explore."
        path="/students/me/career-goals"
        idField="career_goal_id"
        records={records.goals}
        setRecords={(value) =>
          setRecords((current) => ({
            ...current,
            goals:
              typeof value === "function"
                ? value(current.goals)
                : value,
          }))
        }
        fields={[
          {
            name: "career_path_id",
            label: "Career path",
            type: "select",
            options: pathOptions,
            required: true,
          },
          {
            name: "goal_type",
            label: "Goal type",
            type: "select",
            options: [
              { value: "primary", label: "Primary" },
              { value: "secondary", label: "Secondary" },
            ],
          },
          {
            name: "target_date",
            label: "Target date",
            type: "date",
          },
          {
            name: "notes",
            label: "Notes",
            type: "textarea",
          },
        ]}
        formatRecord={(item) => {
          const path = catalogs.paths.find(
            (entry) => Number(entry.career_path_id) === Number(item.career_path_id)
          );
          return (path?.name || item.career_path_name || `Career path #${item.career_path_id}`) +
            " · " + displayLabel(item.goal_type, "Career goal") +
            " · " + displayLabel(item.status, "Active");
        }}
      />

      <RecordSection
        title="Experience"
        description="Add internships, jobs, service, leadership, or campus involvement."
        path="/students/me/experiences"
        idField="experience_id"
        records={records.experiences}
        setRecords={(value) =>
          setRecords((current) => ({
            ...current,
            experiences:
              typeof value === "function"
                ? value(current.experiences)
                : value,
          }))
        }
        fields={[
          {
            name: "experience_type",
            label: "Type",
            type: "text",
            required: true,
          },
          {
            name: "organization_name",
            label: "Organization",
            type: "text",
            required: true,
          },
          {
            name: "position_title",
            label: "Position",
            type: "text",
            required: true,
          },
          {
            name: "location",
            label: "Location",
            type: "text",
          },
          {
            name: "start_date",
            label: "Start date",
            type: "date",
          },
          {
            name: "end_date",
            label: "End date",
            type: "date",
          },
          {
            name: "is_current",
            label: "Current",
            type: "checkbox",
          },
          {
            name: "description",
            label: "Description",
            type: "textarea",
          },
        ]}
        formatRecord={(item) =>
          item.position_title + " at " + item.organization_name
        }
      />

      <RecordSection
        title="Project"
        description="Show academic, personal, research, or professional projects."
        path="/students/me/projects"
        idField="project_id"
        records={records.projects}
        setRecords={(value) =>
          setRecords((current) => ({
            ...current,
            projects:
              typeof value === "function"
                ? value(current.projects)
                : value,
          }))
        }
        fields={[
          {
            name: "project_type",
            label: "Type",
            type: "text",
            required: true,
          },
          {
            name: "title",
            label: "Title",
            type: "text",
            required: true,
          },
          {
            name: "role_title",
            label: "Role",
            type: "text",
          },
          {
            name: "organization_name",
            label: "Organization",
            type: "text",
          },
          {
            name: "start_date",
            label: "Start date",
            type: "date",
          },
          {
            name: "end_date",
            label: "End date",
            type: "date",
          },
          {
            name: "is_current",
            label: "Current",
            type: "checkbox",
          },
          {
            name: "description",
            label: "Description",
            type: "textarea",
          },
          {
            name: "outcome",
            label: "Outcome",
            type: "textarea",
          },
          {
            name: "team_size",
            label: "Team size",
            type: "number",
          },
        ]}
        formatRecord={(item) =>
          item.title +
          (item.role_title ? " · " + item.role_title : "")
        }
      />

      <RecordSection
        title="Certification"
        description="Add certifications, credentials, and licenses."
        path="/students/me/certifications"
        idField="certification_id"
        records={records.certifications}
        setRecords={(value) =>
          setRecords((current) => ({
            ...current,
            certifications:
              typeof value === "function"
                ? value(current.certifications)
                : value,
          }))
        }
        fields={[
          {
            name: "credential_type",
            label: "Type",
            type: "text",
          },
          {
            name: "name",
            label: "Name",
            type: "text",
            required: true,
          },
          {
            name: "issuing_organization",
            label: "Issuing organization",
            type: "text",
            required: true,
          },
          {
            name: "credential_id",
            label: "Credential ID",
            type: "text",
          },
          {
            name: "issue_date",
            label: "Issue date",
            type: "date",
          },
          {
            name: "expiration_date",
            label: "Expiration date",
            type: "date",
          },
          {
            name: "does_not_expire",
            label: "Does not expire",
            type: "checkbox",
          },
          {
            name: "description",
            label: "Description",
            type: "textarea",
          },
        ]}
        formatRecord={(item) =>
          item.name + " · " + item.issuing_organization
        }
      />
    </>
  );
}

// Public career-path catalog.
function CareerPathsView({ healthStatus, onBack, isStudent }) {
  const [paths, setPaths] = useState([]);
  const [goals, setGoals] = useState([]);
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [busyGoalId, setBusyGoalId] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadCatalog() {
      setLoading(true);
      setNotice(null);
      try {
        // The backend limits each request to 50 records. Load every page,
        // including newly published careers beyond the first page.
        const allPaths = [];
        const pageSize = 50;
        for (let offset = 0; offset <= 10000; offset += pageSize) {
          const page = asArray(
            await apiRequest(`/career-paths?limit=${pageSize}&offset=${offset}`),
          );
          allPaths.push(...page);
          if (page.length < pageSize) break;
        }

        const goalResult = isStudent
          ? await apiRequest("/students/me/career-goals")
          : [];

        if (!cancelled) {
          setPaths(
            Array.from(
              new Map(
                allPaths
                  .filter((path) => Boolean(path.is_active))
                  .map((path) => [path.career_path_id, path]),
              ).values(),
            ),
          );
          setGoals(asArray(goalResult));
        }
      } catch (error) {
        if (!cancelled) setNotice({ type: "error", text: error.message });
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadCatalog();
    return () => { cancelled = true; };
  }, [isStudent, refreshKey]);

  async function addGoal(path) {
    if (!isStudent) return;
    setBusyGoalId(path.career_path_id);
    setNotice(null);
    try {
      const saved = await apiRequest("/students/me/career-goals", {
        method: "POST",
        body: JSON.stringify({
          career_path_id: path.career_path_id,
          goal_type: "primary",
          notes:
            "Explore the " +
            path.name +
            " career path.",
        }),
      });

      setGoals((current) => [...current, saved]);

      setNotice({
        type: "success",
        text: path.name + " added to your goals.",
      });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusyGoalId(null);
    }
  }

  async function removeGoal(path, goal) {
    if (!isStudent || !goal) return;
    if (!window.confirm(`Remove ${path.name} from your career goals?`)) return;
    setBusyGoalId(path.career_path_id);
    setNotice(null);
    try {
      await apiRequest(`/students/me/career-goals/${goal.career_goal_id}`, {
        method: "DELETE",
      });
      setGoals((current) =>
        current.filter((item) => Number(item.career_goal_id) !== Number(goal.career_goal_id)),
      );
      setNotice({ type: "success", text: path.name + " removed from your career goals." });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusyGoalId(null);
    }
  }

  const visible = paths.filter(
    (path) =>
      !search ||
      (path.name + " " + path.description)
        .toLowerCase()
        .includes(search.toLowerCase()),
  );

  return (
    <>
      <PageHeader onBack={onBack} />

      <div className="welcome-row">
        <div>
          <p className="eyebrow">Career exploration</p>
          <h1>Explore career paths.</h1>
          <p className="dashboard-intro">
            TigerPad supports students across every JSU major.
          </p>
        </div>

        <HealthPill healthStatus={healthStatus} />
      </div>

      <Notice notice={notice} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", marginTop: "18px" }}>
        <p>{loading ? "Loading published career paths..." : `${paths.length} published career paths`}</p>
        <button type="button" className="secondary-button" disabled={loading} onClick={() => setRefreshKey((current) => current + 1)}>
          {loading ? "Refreshing..." : "Refresh career paths"}
        </button>
      </div>

      <input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search career paths"
        style={{ ...selectStyle, marginTop: "20px" }}
      />

      <div
        className="dashboard-grid"
        style={{ marginTop: "24px" }}
      >
        {!loading && visible.length === 0 && (
          <p>{search ? "No career paths match your search." : "No published career paths are available."}</p>
        )}
        {visible.map((path) => {
          const savedGoal = goals.find(
            (goal) => Number(goal.career_path_id) === Number(path.career_path_id),
          );
          const isBusy = Number(busyGoalId) === Number(path.career_path_id);

          return (
            <article
              className="dashboard-card"
              key={path.career_path_id}
            >
              <p className="card-label">
                {displayLabel(
                  path.career_path_code,
                  "Career path",
                )}
              </p>

              <h2>{path.name}</h2>
              <p>{path.description}</p>

              <p>
                <strong>Typical education:</strong>{" "}
                {path.typical_education_level ||
                  "Varies by position"}
              </p>

              {isStudent && (
                <button
                  type="button"
                  className="secondary-button"
                  disabled={isBusy}
                  onClick={() => savedGoal ? removeGoal(path, savedGoal) : addGoal(path)}
                >
                  {isBusy
                    ? "Saving..."
                    : savedGoal
                      ? "Remove career goal"
                      : "Add as career goal"}
                </button>
              )}
            </article>
          );
        })}
      </div>
    </>
  );
}

// Résumé creation, upload, career matching, analysis, and preview.
function ResumeView({ healthStatus, onBack }) {
  const [resumes, setResumes] = useState([]);
  const [studioTab, setStudioTab] = useState("library");
  const [showUpload, setShowUpload] = useState(false);
  const [editingSuggestion, setEditingSuggestion] = useState(false);
  const [previewMode, setPreviewMode] = useState("suggested");
  const [paths, setPaths] = useState([]);
  const [careerGoals, setCareerGoals] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [reviewTarget, setReviewTarget] = useState("selected");
  const [generatedResumeId, setGeneratedResumeId] = useState(null);
  const [analysisTargetKey, setAnalysisTargetKey] = useState(null);
  const [suggestedDraft, setSuggestedDraft] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [reviewPdfUrl, setReviewPdfUrl] = useState(null);
  const [reviewPdfError, setReviewPdfError] = useState("");
  const [matches, setMatches] = useState([]);
  const [selectedMatch, setSelectedMatch] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    Promise.all([
      apiRequest("/students/me/resumes"),
      loadTigerPadCatalog("/career-paths"),
      apiRequest("/students/me/career-goals"),
    ])
      .then(([resumeResult, pathResult, goalResult]) => {
        const loaded = asArray(resumeResult);
        setResumes(loaded);
        setPaths(asArray(pathResult));
        setCareerGoals(asArray(goalResult));

        const primary = loaded.find((item) => item.is_primary);
        if (primary || loaded[0]) {
          setSelectedId((primary || loaded[0]).resume_id);
        }
      })
      .catch((error) =>
        setNotice({ type: "error", text: error.message }),
      );
  }, []);

  const selected = resumes.find(
    (item) => Number(item.resume_id) === Number(selectedId),
  );

  // Load the original PDF for the AI Review panel without changing the
  // document-preview tab or the student's selected/primary résumé.
  useEffect(() => {
    let active = true;
    let objectUrl = null;
    setReviewPdfUrl(null);
    setReviewPdfError("");
    if (studioTab !== "review" || reviewTarget !== "selected" ||
        !selected || selected.source_type !== "uploaded" ||
        String(selected.file_extension || "").toLowerCase() !== ".pdf") {
      return () => { active = false; };
    }
    _blobRequest(`/students/me/resumes/${selected.resume_id}/file`)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setReviewPdfUrl(objectUrl);
      })
      .catch((error) => { if (active) setReviewPdfError(error.message); });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [studioTab, reviewTarget, selected?.resume_id, selected?.source_type, selected?.file_extension]);

  // Edit only the local suggested draft. Uploaded originals are never modified.
  function editDraftField(field, value) {
    if (reviewTarget === "draft") { setAnalysis(null); setAnalysisTargetKey(null); }
    setSuggestedDraft((current) => current ? {
      ...current, draft: { ...current.draft, [field]: value },
    } : current);
  }

  function editDraftItem(section, index, field, value) {
    if (reviewTarget === "draft") { setAnalysis(null); setAnalysisTargetKey(null); }
    setSuggestedDraft((current) => current ? {
      ...current,
      draft: {
        ...current.draft,
        [section]: (current.draft?.[section] || []).map((item, i) =>
          i === index ? { ...item, [field]: value } : item),
      },
    } : current);
  }

  function saveSuggestedPdf() {
    if (!suggestedDraft?.draft) return;
    setEditingSuggestion(false);
    // Browser print dialog supports Save as PDF without requiring a new backend route.
    window.setTimeout(() => window.print(), 50);
  }

  async function uploadResume(event) {
    event.preventDefault();

    if (!file) {
      setNotice({
        type: "error",
        text: "Choose a PDF or DOCX file first.",
      });
      return;
    }

    setBusy(true);

    try {
      const data = new FormData();
      data.append("file", file);
      data.append(
        "title",
        file.name.replace(/\.[^/.]+$/, ""),
      );
      data.append("resume_type", "general");

      const saved = await uploadRequest(
        "/students/me/resumes/upload",
        data,
      );

      await apiRequest(`/students/me/resumes/${saved.resume_id}`, {
        method: "PATCH", body: JSON.stringify({ is_primary: true }),
      });
      setResumes((current) => [{ ...saved, is_primary: true }, ...current.map((item) => ({ ...item, is_primary: false }))]);
      setSelectedId(saved.resume_id);
      setStudioTab("preview");
      setShowUpload(false);
      setFile(null);

      setNotice({
        type: "success",
        text: "Résumé uploaded.",
      });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  // Save the exact, potentially edited profile draft as structured résumé content.
  // This uses the existing résumé API and never changes the primary selection.
  async function persistGeneratedDraft() {
    if (!suggestedDraft?.draft) throw new Error("Generate a résumé from your profile first.");
    const payload = {
      title: `${suggestedDraft.draft.name || "Student"} - Profile résumé`.slice(0, 150),
      resume_type: "general",
      template_name: "profile_builder",
      content_json: suggestedDraft.draft,
    };
    if (generatedResumeId) {
      const updated = await apiRequest(`/students/me/resumes/${generatedResumeId}`, {
        method: "PATCH", body: JSON.stringify(payload),
      });
      setResumes((current) => current.map((item) =>
        Number(item.resume_id) === Number(updated.resume_id) ? updated : item));
      return updated;
    }
    const saved = await apiRequest("/students/me/resumes", {
      method: "POST", body: JSON.stringify(payload),
    });
    setGeneratedResumeId(saved.resume_id);
    setResumes((current) => [saved, ...current]);
    return saved;
  }

  async function analyze() {
    if (reviewTarget === "draft" && !suggestedDraft?.draft) return;
    if (reviewTarget === "selected" && !selected) return;

    setBusy(true);

    try {
      if (reviewTarget === "draft") {
        const savedDraft = await persistGeneratedDraft();
        const result = await apiRequest(
          `/students/me/resumes/${savedDraft.resume_id}/analyze`,
          {
            method: "POST",
            body: JSON.stringify({
              analysis_method: "hybrid",
              career_path_id: savedDraft.career_path_id || null,
            }),
          },
        );
        setAnalysis(result);
        setAnalysisTargetKey("draft");
        setMatches([]);
        setStudioTab("review");
        setNotice({ type: "success", text: "Your profile-built résumé was reviewed. Your selected résumé is unchanged." });
        return;
      }
      if (!selected.career_path_id) {
        const result = await apiRequest(
          "/students/me/resumes/" +
            selected.resume_id +
            "/career-matches",
          {
            method: "POST",
            body: JSON.stringify({
              analysis_method: "hybrid",
              limit: 3,
            }),
          },
        );

        setMatches(asArray(result));

        setSelectedMatch(
          result?.[0]?.career_path_id
            ? String(result[0].career_path_id)
            : "",
        );

        setNotice({
          type: "success",
          text: "Choose a career match before analysis.",
        });
      } else {
        const result = await apiRequest(
          "/students/me/resumes/" +
            selected.resume_id +
            "/analyze",
          {
            method: "POST",
            body: JSON.stringify({
              analysis_method: "hybrid",
            }),
          },
        );

        setAnalysis(result);
        setAnalysisTargetKey("selected");
        setStudioTab("review");

        setNotice({
          type: "success",
          text: "Résumé analysis completed.",
        });
      }
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function chooseMatch() {
    if (!selectedMatch) return;

    setBusy(true);

    try {
      await apiRequest(
        "/students/me/resumes/" +
          selected.resume_id +
          "/career-matches/select",
        {
          method: "POST",
          body: JSON.stringify({
            career_path_id: Number(selectedMatch),
          }),
        },
      );

      const result = await apiRequest(
        "/students/me/resumes/" +
          selected.resume_id +
          "/analyze",
        {
          method: "POST",
          body: JSON.stringify({
            career_path_id: Number(selectedMatch),
            analysis_method: "hybrid",
          }),
        },
      );

      setResumes((current) =>
        current.map((item) =>
          item.resume_id === selected.resume_id
            ? {
                ...item,
                career_path_id: Number(selectedMatch),
              }
            : item,
        ),
      );

      setAnalysis(result);
      setAnalysisTargetKey("selected");
      setStudioTab("review");
      setMatches([]);

      setNotice({
        type: "success",
        text: "Career path selected and résumé analyzed.",
      });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function generateSuggestedDraft() {
    setBusy(true);
    try {
      const response = await apiRequest(
        "/students/me/resumes/draft-preview" +
          (selected?.career_path_id ? "?career_path_id=" + selected.career_path_id : ""),
        { method: "POST" },
      );
      setSuggestedDraft(response);
      setGeneratedResumeId(null);
      setReviewTarget("draft");
      setAnalysis(null);
      setAnalysisTargetKey(null);
      setMatches([]);
      setEditingSuggestion(false);
      setPreviewMode("suggested");
      setStudioTab("preview");
      setNotice({ type: "success", text: "Profile-based résumé suggestion is ready." });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function previewOriginalResume() {
    if (!selected || selected.source_type !== "uploaded") return;
    setBusy(true);
    try {
      const blob = await _blobRequest(
        "/students/me/resumes/" + selected.resume_id + "/file",
      );
      const url = URL.createObjectURL(blob);
      setPreviewMode("original");
      setStudioTab("preview");
      setPreviewUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return url;
      });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function loadSavedAnalysis(resume) {
    try {
      const result = await apiRequest(
        "/students/me/resumes/" + resume.resume_id + "/analyses",
      );
      setAnalysis(asArray(result).find((item) => item.analysis_status === "completed") || null);
      setAnalysisTargetKey("selected");
    } catch {
      setAnalysis(null);
    }
  }

  const content = selected?.content_json || {};
  // Student-selected primary goal is the source of truth for this dashboard.
  // A résumé's career_path_id is only its individual analysis target.
  const currentGoals = careerGoals.filter((goal) =>
    !["removed", "deleted", "cancelled", "inactive"].includes(String(goal.status || "").toLowerCase())
  );
  const primaryGoal = currentGoals.find((goal) => goal.goal_type === "primary") || currentGoals[0];
  const activeCareer = paths.find((path) =>
    Number(path.career_path_id) === Number(primaryGoal?.career_path_id)
  );
  const scoreParts = analysis ? [
    ["Content", analysis.content_score], ["Formatting", analysis.format_score],
    ["Impact", analysis.impact_score], ["Career alignment", analysis.career_alignment_score],
  ] : [];
  const navy = "#09254a";
  const gold = "#1597d4";
  const panel = { background: "#102b4b", color: "#e8f2ff", border: "1px solid #254b73", borderRadius: 18, padding: 22, boxShadow: "0 5px 22px rgba(0,0,0,.12)" };
  const soft = { background: "#173657", color: "#e8f2ff", border: "1px solid #315575", borderRadius: 12, padding: 16 };
  const tabButton = (id, label) => ({
    type: "button", onClick: () => setStudioTab(id),
    style: { padding: "12px 18px", border: "none", borderBottom: studioTab === id ? `3px solid ${gold}` : "3px solid transparent", background: studioTab === id ? "#214a71" : "transparent", color: "#f1f7ff", fontWeight: studioTab === id ? 800 : 600, cursor: "pointer", borderRadius: "9px 9px 0 0" },
  });
  // Remove an older résumé from the student's active library. The backend
  // performs an ownership-checked soft delete and preserves audit history.
  async function deleteSavedResume(item) {
    if (busy) return;
    if (!window.confirm(`Remove "${item.title}" from your résumé library? This will hide it from your active résumés.`)) return;
    setBusy(true);
    try {
      await apiRequest(`/students/me/resumes/${item.resume_id}`, { method: "DELETE" });
      const remaining = resumes.filter((resume) => Number(resume.resume_id) !== Number(item.resume_id));
      setResumes(remaining);
      if (Number(selectedId) === Number(item.resume_id)) {
        if (remaining[0]) {
          await apiRequest(`/students/me/resumes/${remaining[0].resume_id}`, {
            method: "PATCH", body: JSON.stringify({ is_primary: true }),
          });
          setResumes(remaining.map((resume, index) => ({ ...resume, is_primary: index === 0 })));
        }
        setSelectedId(remaining[0]?.resume_id ?? null);
        setAnalysis(null);
        setSuggestedDraft(null);
        setMatches([]);
        setSelectedMatch("");
        setPreviewUrl((previous) => {
          if (previous) URL.revokeObjectURL(previous);
          return null;
        });
      }
      setNotice({ type: "success", text: `Removed "${item.title}" from your résumé library.` });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function chooseResume(item) {
    try {
      await apiRequest(`/students/me/resumes/${item.resume_id}`, {
        method: "PATCH", body: JSON.stringify({ is_primary: true }),
      });
      setResumes((current) => current.map((resume) => ({
        ...resume, is_primary: Number(resume.resume_id) === Number(item.resume_id),
      })));
    } catch (error) {
      setNotice({ type: "error", text: `Could not select résumé: ${error.message}` });
      return;
    }
    setSelectedId(item.resume_id);
    setAnalysis(null);
    setReviewTarget("selected");
    setPreviewMode("selected");
    setAnalysisTargetKey(null);
    setEditingSuggestion(false);
    setPreviewUrl((previous) => { if (previous) URL.revokeObjectURL(previous); return null; });
    setMatches([]);
    setStudioTab("preview");
    loadSavedAnalysis(item);
  }
  const draft = suggestedDraft?.draft;
  const draftSections = draft ? [
    ["Professional summary", draft.summary],
    ["Education", [draft.education?.institution, draft.education?.major, draft.education?.expected_graduation_date ? `Expected graduation: ${draft.education.expected_graduation_date}` : ""].filter(Boolean).join(" · ")],
  ] : [];
  const textValue = (value) => Array.isArray(value) ? value.join(" · ") : typeof value === "string" ? value : "";

  return (
    <>
      <PageHeader onBack={onBack} />
      <style>{`
        .resume-studio-shell input:not([type="radio"]):not([type="checkbox"]),
        .resume-studio-shell select, .resume-studio-shell textarea {
          background: #0b2340 !important; color: #f1f7ff !important;
          border: 1px solid #416587 !important;
        }
        .resume-studio-shell input::placeholder, .resume-studio-shell textarea::placeholder { color: #a8bdd5 !important; }
        .resume-studio-shell option { background: #0b2340; color: #f1f7ff; }
      `}</style>
      <section style={{ background: `linear-gradient(115deg, ${navy}, #123d72)`, color: "#fff", borderRadius: 20, padding: "30px 32px", marginTop: 14 }}>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
          <div>
            <p style={{ color: "#8bd4ff", fontSize: 12, fontWeight: 800, letterSpacing: 2, textTransform: "uppercase", margin: "0 0 8px" }}>TigerPad · Student career tools</p>
            <h1 style={{ color: "white", fontSize: "clamp(28px, 4vw, 40px)", margin: "0 0 8px" }}>Résumé Studio</h1>
            <p style={{ color: "#dbe7f8", margin: 0, maxWidth: 550 }}>Your professional résumé workspace. Upload an existing résumé or generate one from your profile, customize it, and get career-focused feedback.</p>
          </div>
          <HealthPill healthStatus={healthStatus} />
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 26 }}>
          <button type="button" className="primary-button" onClick={generateSuggestedDraft} disabled={busy} style={{ background: gold, color: "#fff", borderColor: gold }}>✦ Generate résumé</button>
          <button type="button" className="secondary-button" onClick={() => { setStudioTab("upload"); setShowUpload(true); }} style={{ background: "#ffffff16", color: "white", border: "1px solid #a6bbd5" }}>↑ Upload existing</button>
          <button type="button" className="secondary-button" onClick={generateSuggestedDraft} disabled={busy} style={{ background: "#ffffff16", color: "white", border: "1px solid #a6bbd5" }}>✦ Build from my profile</button>
        </div>
      </section>
      <Notice notice={notice} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 14, margin: "20px 0" }}>
        {[
          ["Saved résumés", resumes.length, "Documents in your library"],
          ["Résumé score", analysis?.overall_score == null ? "—" : `${displayScore(analysis.overall_score)}%`, "Most recently selected analysis"],
          ["Selected career", activeCareer?.name || "No career goal selected", "From your Career Paths goals"],
        ].map(([label, value, hint]) => <div key={label} style={panel}><div style={{ color: "#b8cce2", fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: .6 }}>{label}</div><div style={{ color: "#f3f8ff", fontSize: label === "Selected career" ? 18 : 29, fontWeight: 800, margin: "8px 0" }}>{value}</div><div style={{ color: "#b8cce2", fontSize: 12 }}>{hint}</div></div>)}
      </div>
      {/* Always-visible selection summary: this is the saved résumé currently open,
          not necessarily the student's primary résumé or latest upload. */}
      <section aria-label="Currently selected résumé" style={{ ...panel, marginBottom: 20, border: "1px solid #3973a2" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          <div style={{ flex: "1 1 280px", minWidth: 0 }}>
            <div style={{ color: "#9ddfff", fontSize: 12, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Currently selected résumé</div>
            {selected ? <>
              <h2 style={{ margin: "0 0 7px", color: "#f3f8ff", fontSize: 23, overflowWrap: "anywhere" }}>{selected.title}</h2>
              <p style={{ margin: 0, color: "#c1d7ee", fontSize: 14 }}>
                {displayLabel(selected.resume_type, "General")} · {selected.source_type === "uploaded" ? "Uploaded document" : "Created in TigerPad"}
                {selected.is_primary ? " · Primary résumé" : ""}
              </p>
            </> : <p style={{ margin: 0, color: "#c1d7ee" }}>No résumé selected. Choose one from your library.</p>}
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button type="button" className="secondary-button" onClick={() => setStudioTab("library")}
              style={{ background: "#214a71", color: "#f3f8ff", border: "1px solid #5486b2" }}>
              Choose résumé
            </button>
            {selected && <button type="button" className="primary-button" onClick={() => setStudioTab("preview")}
              style={{ background: "#1597d4", color: "#fff", border: "1px solid #1597d4" }}>
              View selected résumé →
            </button>}
          </div>
        </div>
      </section>
      <div className="resume-studio-shell" style={{ ...panel, padding: 0, overflow: "hidden" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 3, padding: "12px 16px 0", borderBottom: "1px solid #315575" }}>
          <button {...tabButton("library", "My résumés")}>My résumés</button>
          <button {...tabButton("upload", "Upload résumé")}>Builder & upload</button>
          <button {...tabButton("preview", "Document preview")}>Document preview</button>
          <button {...tabButton("review", "AI review")}>AI review</button>
        </div>
        <div style={{ padding: "24px", minHeight: 320 }}>
          {studioTab === "library" && <>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", alignItems: "center", gap: 12, marginBottom: 20 }}><div><h2 style={{ margin: "0 0 5px", color: "#f3f8ff" }}>My résumé library</h2><p style={{ margin: 0, color: "#b8cce2" }}>Choose a résumé to preview or improve.</p></div><button type="button" className="secondary-button" onClick={() => setStudioTab("upload")}>Upload résumé</button></div>
            {resumes.length === 0 ? <div style={{ ...soft, textAlign: "center", padding: 42 }}><h3>No résumés saved yet</h3><p>Generate a résumé from your profile or upload an existing PDF/DOCX.</p><button className="primary-button" type="button" onClick={() => setStudioTab("upload")}>Upload résumé</button></div> :
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 14 }}>
                {resumes.map((item) => (
                  <div key={item.resume_id} style={{ ...soft, display: "flex", flexDirection: "column", gap: 12, border: Number(selectedId) === Number(item.resume_id) ? `2px solid ${gold}` : "1px solid #315575", background: Number(selectedId) === Number(item.resume_id) ? "#214a71" : "#173657" }}>
                    <button type="button" onClick={() => chooseResume(item)} style={{ background: "transparent", border: "none", padding: 0, textAlign: "left", cursor: "pointer", color: "#f3f8ff", flex: 1, minWidth: 0, width: "100%" }}>
                      <div style={{ fontSize: 28, marginBottom: 12 }}>▤</div>
                      <strong style={{ color: "#f3f8ff", display: "block", fontSize: 16, lineHeight: 1.5, whiteSpace: "normal", overflowWrap: "anywhere", wordBreak: "break-word", maxWidth: "100%" }}>{item.title}</strong>{Number(selectedId) === Number(item.resume_id) && <span style={{ display: "inline-block", margin: "8px 0 4px", color: "#b8ebff", fontSize: 12, fontWeight: 800 }}>✓ SELECTED</span>}
                      <span style={{ color: "#b8cce2", fontSize: 12 }}>{displayLabel(item.resume_type, "General")} · {item.source_type === "uploaded" ? "Uploaded" : "Created in TigerPad"}</span>
                      <div style={{ marginTop: 15, color: "#8ed8ff", fontWeight: 800, fontSize: 13, textDecoration: "underline", textUnderlineOffset: 3 }}>Open résumé →</div>
                    </button>
                    <button type="button" disabled={busy} onClick={() => deleteSavedResume(item)} aria-label={`Delete résumé ${item.title}`} style={{ alignSelf: "flex-start", background: "transparent", color: "#ffb8bf", border: "1px solid #ad6570", borderRadius: 8, padding: "8px 12px", fontSize: 13, fontWeight: 700, cursor: busy ? "not-allowed" : "pointer", opacity: busy ? .6 : 1 }}>
                      Delete résumé
                    </button>
                  </div>
                ))}
              </div>}
          </>}
          {studioTab === "upload" && <>
            <h2 style={{ color: "#f3f8ff", marginTop: 0 }}>Upload an existing résumé</h2>
            <p style={{ color: "#b8cce2" }}>Keep your original PDF or DOCX in TigerPad for preview and AI review. Your uploaded file will not be changed by profile-based suggestions.</p>
            <section style={{ ...soft, maxWidth: 620, marginTop: 18 }}>
              <form className="auth-form" onSubmit={uploadResume} style={{ color: "#e8f2ff" }}>
                <label>PDF or DOCX file
                  <input type="file" accept=".pdf,.docx" onChange={(event) => setFile(event.target.files?.[0] || null)} required />
                </label>
                {file && <p style={{ fontSize: 13 }}>{file.name}</p>}
                <button className="primary-button" disabled={busy}>{busy ? "Uploading..." : "Upload résumé"}</button>
              </form>
            </section>
            <div style={{ ...soft, marginTop: 18 }}>
              <h3 style={{ color: "#f3f8ff", marginTop: 0 }}>Want to create a new résumé instead?</h3>
              <p>Generate one from your saved TigerPad profile, then edit the suggestion and save it as a PDF.</p>
              <button type="button" className="secondary-button" disabled={busy} onClick={generateSuggestedDraft}>✦ Generate from my profile</button>
            </div>
          </>}
          <style>{`@media print {
            @page { size: letter; margin: 0.55in; }
            body * { visibility: hidden !important; }
            .tigerpad-resume-paper, .tigerpad-resume-paper * { visibility: visible !important; }
            .tigerpad-resume-paper { position: absolute !important; top: 0 !important; left: 0 !important; width: 100% !important; max-width: none !important; min-height: 0 !important; margin: 0 !important; padding: 0 !important; border: none !important; box-shadow: none !important; }
            .tigerpad-resume-paper section, .tigerpad-resume-paper div { break-inside: avoid; }
          }`}</style>
          {/* The printable page is intentionally white; its text must remain dark even under the global dark theme. */}
          <style>{`.tigerpad-resume-paper, .tigerpad-resume-paper p, .tigerpad-resume-paper strong, .tigerpad-resume-paper li, .tigerpad-resume-paper span { color: #172b47 !important; } .tigerpad-resume-paper h2, .tigerpad-resume-paper h3 { color: #102d50 !important; } .tigerpad-resume-paper { color-scheme: light; }`}</style>
          {studioTab === "preview" && <>
            {previewMode === "suggested" && (
              <div
                role="note"
                style={{
                  background: "#173657",
                  border: "1px solid #3986bd",
                  borderLeft: "4px solid #38bdf8",
                  borderRadius: 12,
                  padding: "16px 20px",
                  marginBottom: 20,
                  color: "#e8f2ff",
                }}
              >
                <strong style={{ display: "block", marginBottom: 8, color: "#ffffff", fontSize: 15 }}>
                  About This Suggested Résumé
                </strong>
                <p style={{ margin: 0, lineHeight: 1.7, color: "#d5e8f8", fontSize: 14 }}>
                  This résumé is automatically generated using information saved in your TigerPad
                  student profile, including your education, skills, projects, certifications,
                  and work experience. It is not an exact reproduction of your uploaded résumé.
                  Please review all information for accuracy before downloading, sharing, or using it.
                </p>
              </div>
            )}
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 18 }}><div><h2 style={{ color: "#f3f8ff", margin: 0 }}>Document preview</h2><p style={{ color: "#b8cce2", margin: "6px 0 0" }}>{selected?.title || "Choose a résumé or generate a profile-based draft"}</p></div><div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}><button type="button" className="secondary-button" disabled={busy} onClick={generateSuggestedDraft}>✦ Suggested version</button>{selected?.source_type === "uploaded" && <button type="button" className="secondary-button" disabled={busy} onClick={previewOriginalResume}>Original file</button>}</div></div>
            {previewMode === "suggested" && draft && (
              <div style={{ ...soft, marginBottom: 18 }}>
                <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
                  <button type="button" className="secondary-button" onClick={() => setEditingSuggestion((current) => !current)}>
                    {editingSuggestion ? "✓ Finish editing" : "✎ Edit suggested résumé"}
                  </button>
                  <button type="button" className="primary-button" onClick={saveSuggestedPdf}>↓ Save as PDF</button>
                </div>
                <p style={{ fontSize: 13, marginBottom: 0 }}>Edits apply to this preview only and do not change your student profile or uploaded original. Save a PDF before leaving this page.</p>
                {editingSuggestion && (
                  <div className="auth-form" style={{ marginTop: 16 }}>
                    {[['name', 'Full name'], ['email', 'Email'], ['headline', 'Headline'], ['summary', 'Professional summary']].map(([field, label]) => (
                      <label key={field}>{label}
                        <textarea rows={field === 'summary' ? 4 : 2} style={textareaStyle} value={draft[field] || ''} onChange={(event) => editDraftField(field, event.target.value)} />
                      </label>
                    ))}
                    <label>Skills (one per line)
                      <textarea rows={4} style={textareaStyle} value={(draft.skills || []).join('\n')} onChange={(event) => editDraftField('skills', event.target.value.split('\n').map((value) => value.trim()).filter(Boolean))} />
                    </label>
                    {['experiences', 'projects', 'certifications'].map((section) => (draft[section] || []).length > 0 && (
                      <div key={section}>
                        <h3 style={{ color: '#f3f8ff', textTransform: 'capitalize' }}>{section}</h3>
                        {draft[section].map((item, index) => (
                          <div key={index} style={{ ...soft, marginBottom: 12 }}>
                            <label>Title / name
                              <input value={item.job_title || item.title || item.name || ''} onChange={(event) => editDraftItem(section, index, item.job_title !== undefined ? 'job_title' : item.title !== undefined ? 'title' : 'name', event.target.value)} />
                            </label>
                            <label>Description
                              <textarea rows={3} style={textareaStyle} value={textValue(item.description || item.achievements || item.responsibilities || item.technologies)} onChange={(event) => editDraftItem(section, index, 'description', event.target.value)} />
                            </label>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {previewMode === "original" && previewUrl && selected?.source_type === "uploaded" ? <div style={{ ...soft, background: "#e8edf5" }}>{selected.file_extension === ".pdf" ? <iframe src={previewUrl} title="Original uploaded résumé" style={{ width: "100%", height: 650, border: 0, background: "white" }} /> : <a href={previewUrl} download={selected.original_file_name || "resume.docx"}>Download original DOCX to view it</a>}</div> :
              previewMode === "suggested" && draft ? <div className="tigerpad-resume-paper" style={{ maxWidth: 780, margin: "0 auto", background: "white", color: "#172b47", border: "1px solid #d8e0e9", boxShadow: "0 12px 36px rgba(0,0,0,.1)", padding: "clamp(20px,5vw,54px)", minHeight: 650 }}><div style={{ borderBottom: `3px solid ${navy}`, paddingBottom: 17, marginBottom: 24, textAlign: "center" }}><h2 style={{ margin: 0, color: navy, textTransform: "uppercase", letterSpacing: 1.5 }}>{draft.name || "Student résumé"}</h2><p style={{ margin: "7px 0", color: "#475569" }}>{draft.email || ""}</p>{draft.headline && <p style={{ margin: 0 }}>{draft.headline}</p>}</div>{draftSections.map(([label, value]) => value ? <section key={label} style={{ marginBottom: 22 }}><h3 style={{ borderBottom: "1px solid #cbd5e1", color: navy, textTransform: "uppercase", letterSpacing: .8, fontSize: 14, paddingBottom: 7 }}>{label}</h3><p style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{value}</p></section> : null)}{draft.skills?.length > 0 && <section><h3 style={{ color: navy, borderBottom: "1px solid #cbd5e1" }}>SKILLS</h3><p>{draft.skills.join(" · ")}</p></section>}{[["EXPERIENCE", draft.experiences], ["PROJECTS", draft.projects], ["CERTIFICATIONS", draft.certifications]].map(([label, items]) => items?.length ? <section key={label} style={{ marginTop: 22 }}><h3 style={{ color: navy, borderBottom: "1px solid #cbd5e1", paddingBottom: 6, fontSize: 14 }}>{label}</h3>{items.map((item, index) => <div key={index} style={{ marginBottom: 15 }}><strong>{item.job_title || item.title || item.name || "Entry"}</strong><p style={{ margin: "3px 0", fontSize: 13 }}>{item.organization_name || item.company_name || item.employer || item.issuer || ""}</p><p style={{ margin: "5px 0", whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{textValue(item.description || item.achievements || item.responsibilities || item.technologies)}</p></div>)}</section> : null)}<p style={{ fontSize: 12, color: "#b8cce2", borderTop: "1px solid #e2e8f0", paddingTop: 12 }}>Profile-based suggestion. Verify every detail before using this résumé.</p></div> :
              selected?.source_type === "generated" ? <div className="tigerpad-resume-paper" style={{ maxWidth: 780, margin: "auto", padding: 45, background: "white", color: "#172b47", border: "1px solid #d8e0e9", minHeight: 380 }}><h2 style={{ color: "#102d50" }}>{selected.title}</h2><hr/><h3 style={{ color: "#102d50" }}>Professional summary</h3><p>{content.summary || "No summary added yet."}</p><h3 style={{ color: "#102d50" }}>Career focus</h3><p>{content.career_focus || "Not specified"}</p><h3 style={{ color: "#102d50" }}>Skills</h3><p>{Array.isArray(content.skills) ? content.skills.join(" · ") : "No skills added yet."}</p></div> :
              <div style={{ ...soft, textAlign: "center", padding: 40 }}><h3>No document open</h3><p>Select a résumé from your library, open the original file, or generate a suggested version from your profile.</p><button type="button" className="secondary-button" onClick={() => setStudioTab("library")}>Browse my résumés</button></div>}
            {draft && previewMode !== "original" && <div style={{ ...soft, marginTop: 18 }}><strong>Before you use this draft</strong><p>{suggestedDraft?.notice}</p>{suggestedDraft?.missing_information?.length > 0 && <><h4>Information to add</h4><FeedbackList value={suggestedDraft.missing_information} /></>}</div>}
          </>}
          {studioTab === "review" && <>
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 14 }}><div><h2 style={{ color: "#f3f8ff", margin: 0 }}>Résumé review</h2><p style={{ color: "#b8cce2", marginTop: 6 }}>Career alignment, strengths, and improvement opportunities.</p></div></div>
            <div style={{ ...soft, marginTop: 18 }}>
              <h3 style={{ margin: "0 0 8px", color: "#f3f8ff", fontSize: 18 }}>Step 1: Select a résumé to review</h3>
              <p style={{ color: "#b8cce2", margin: "0 0 16px" }}>Choose one option below. The highlighted card is the résumé the AI will analyze.</p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
                <button type="button" onClick={() => { setReviewTarget("selected"); setAnalysis(null); setAnalysisTargetKey(null); setMatches([]); if (selected) loadSavedAnalysis(selected); }}
                  style={{ textAlign: "left", padding: 18, borderRadius: 12, cursor: "pointer", border: reviewTarget === "selected" ? "2px solid #38bdf8" : "1px solid #55718f", background: reviewTarget === "selected" ? "#174c73" : "#102b4b", color: "#f3f8ff", minHeight: 116 }}>
                  <strong style={{ display: "block", fontSize: 16, marginBottom: 9 }}>{reviewTarget === "selected" ? "✓ " : ""}Saved résumé from my library</strong>
                  <span style={{ display: "block", fontSize: 13, color: "#d0e2f5" }}>{selected ? selected.title : "No résumé selected — choose one from My résumés"}</span>
                </button>
                <button type="button" disabled={!draft} onClick={() => { setReviewTarget("draft"); setAnalysis(null); setAnalysisTargetKey(null); setMatches([]); }}
                  style={{ textAlign: "left", padding: 18, borderRadius: 12, cursor: draft ? "pointer" : "not-allowed", opacity: draft ? 1 : 0.6, border: reviewTarget === "draft" ? "2px solid #38bdf8" : "1px solid #55718f", background: reviewTarget === "draft" ? "#174c73" : "#102b4b", color: "#f3f8ff", minHeight: 116 }}>
                  <strong style={{ display: "block", fontSize: 16, marginBottom: 9 }}>{reviewTarget === "draft" ? "✓ " : ""}Résumé built from my profile</strong>
                  <span style={{ display: "block", fontSize: 13, color: "#d0e2f5" }}>{draft ? "Ready — includes your latest edits" : "Not generated yet — use Builder & upload first"}</span>
                </button>
              </div>
              <p style={{ color: "#b8cce2", fontSize: 13, margin: "14px 0 0" }}>Your library selection and primary résumé will not change when you review a profile-built résumé.</p>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 12, marginTop: 18 }}>
              <div><strong style={{ color: "#f3f8ff" }}>Step 2: Run AI Review</strong><p style={{ margin: "5px 0 0", color: "#b8cce2", fontSize: 13 }}>Reviewing: {reviewTarget === "draft" ? "Résumé built from my profile" : selected?.title || "No library résumé selected"}</p></div>
              <button className="primary-button" type="button" onClick={analyze} disabled={busy || (reviewTarget === "draft" ? !draft : !selected)}>{busy ? "Analyzing..." : "Analyze this résumé with AI"}</button>
            </div>
            {reviewTarget === "selected" && !selected && <div style={{ ...soft, marginTop: 20 }}>Select a saved résumé from My résumés to run an analysis.</div>}
            {reviewTarget === "draft" && !draft && <div style={{ ...soft, marginTop: 20 }}>Build a résumé from your profile before requesting a review.</div>}
            {reviewTarget === "selected" && matches.length > 0 && <div style={{ ...soft, marginTop: 20 }}><h3>Choose a career match</h3>{matches.map(match => <label key={match.career_path_id} style={{ display: "block", padding: 12, background: "#102b4b", color: "#e8f2ff", borderRadius: 9, marginBottom: 8 }}><input type="radio" name="resume-match" value={match.career_path_id} checked={Number(selectedMatch) === Number(match.career_path_id)} onChange={event => setSelectedMatch(event.target.value)} /> <strong>{match.name}</strong> · {displayScore(match.confidence_score)}%<p style={{ margin: "6px 0 0", fontSize: 13 }}>{match.reason}</p></label>)}<button className="primary-button" type="button" disabled={busy || !selectedMatch} onClick={chooseMatch}>Select career and analyze</button></div>}
            <div className="resume-review-workspace">
              <section className="resume-review-document">
                <div className="resume-review-document-header">
                  <div><h3>Résumé preview</h3><p>Compare the actual résumé with the AI recommendations.</p></div>
                  {reviewTarget === "draft" && draft && <button className="secondary-button" type="button" onClick={() => { setPreviewMode("suggested"); setEditingSuggestion(true); setStudioTab("preview"); }}>Edit résumé</button>}
                  {reviewTarget === "selected" && selected?.source_type === "uploaded" && <button className="secondary-button" type="button" onClick={previewOriginalResume}>Open full document</button>}
                </div>
                {reviewTarget === "draft" && draft ? (
                  <div className="resume-review-paper">
                    <h2>{draft.name || "Student résumé"}</h2>
                    <p className="resume-review-contact">{draft.email || ""}{draft.headline ? ` · ${draft.headline}` : ""}</p>
                    {draftSections.map(([label, value]) => value ? <section key={label}><h4>{label}</h4><p>{value}</p></section> : null)}
                    {draft.skills?.length > 0 && <section><h4>Skills</h4><p>{draft.skills.join(" · ")}</p></section>}
                    {([["Experience", draft.experiences], ["Projects", draft.projects], ["Certifications", draft.certifications]]).map(([label, items]) =>
                      items?.length ? <section key={label}><h4>{label}</h4>{items.map((item, index) => <div key={index} className="resume-review-entry"><strong>{item.job_title || item.title || item.name || "Entry"}</strong><p>{item.organization_name || item.company_name || item.employer || item.issuer || ""}</p><p>{textValue(item.description || item.achievements || item.responsibilities || item.technologies)}</p></div>)}</section> : null
                    )}
                  </div>
                ) : reviewTarget === "selected" && selected?.source_type === "uploaded" && String(selected.file_extension || "").toLowerCase() === ".pdf" ? (
                  reviewPdfUrl ? <iframe className="resume-review-pdf" title={`Preview of ${selected.title}`} src={reviewPdfUrl} /> :
                    <div className="resume-review-empty">{reviewPdfError ? `Preview unavailable: ${reviewPdfError}` : "Loading PDF preview…"}</div>
                ) : reviewTarget === "selected" && selected?.source_type === "uploaded" ? (
                  <div className="resume-review-empty"><p>This uploaded DOCX cannot be displayed directly in the browser.</p><p>Open the original document to view it while using the AI feedback here.</p><button className="secondary-button" type="button" onClick={previewOriginalResume}>Open DOCX</button></div>
                ) : reviewTarget === "selected" && selected ? (
                  <div className="resume-review-paper">
                    <h2>{selected.title}</h2>
                    {Object.entries(content).filter(([key, value]) => value != null && value !== "" && !["metadata", "id"].includes(key)).map(([key, value]) =>
                      <section key={key}><h4>{displayLabel(key)}</h4><p>{Array.isArray(value) ? value.map((v) => typeof v === "object" ? Object.values(v).filter(x => typeof x === "string").join(" · ") : String(v)).join("\n") : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}</p></section>
                    )}
                  </div>
                ) : <div className="resume-review-empty">Choose a résumé above to see its preview.</div>}
              </section>
              <section className="resume-review-feedback">
                <h3>AI feedback</h3>
                <p>Use the results to identify which sections to improve, then review again.</p>
            {analysis && analysisTargetKey === reviewTarget ? <div style={{ marginTop: 22 }}><div style={{ ...soft, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 20 }}><div style={{ fontSize: 42, fontWeight: 900, color: "#f3f8ff" }}>{displayScore(analysis.overall_score)}<span style={{ fontSize: 18 }}>/100</span></div><div><h3 style={{ margin: "0 0 5px", color: "#f3f8ff" }}>Overall résumé score</h3><p style={{ margin: 0 }}>{analysis.summary}</p></div></div><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 15, marginTop: 20 }}>{scoreParts.map(([label, score]) => <div key={label} style={soft}><strong style={{ color: "#f3f8ff" }}>{label}</strong><p style={{ fontSize: 25, fontWeight: 800, margin: "8px 0" }}>{displayScore(score)}%</p><div style={{ background: "#dbe4ee", height: 8, borderRadius: 10, overflow: "hidden" }}><div style={{ background: gold, height: "100%", width: `${Math.max(0, Math.min(100, Number(score) || 0))}%` }} /></div></div>)}</div><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 18, marginTop: 20 }}><section style={soft}><h3 style={{ color: "#f3f8ff" }}>✓ Strengths</h3><FeedbackList value={analysis.strengths_json} /></section><section style={soft}><h3 style={{ color: "#f3f8ff" }}>↗ Improvements</h3><FeedbackList value={analysis.improvements_json} /></section></div>{analysis.section_feedback_json && <div style={{ ...soft, marginTop: 18 }}><h3 style={{ color: "#f3f8ff" }}>Section feedback</h3><FeedbackList value={analysis.section_feedback_json} /></div>}</div> : (reviewTarget === "draft" ? Boolean(draft) : Boolean(selected)) && matches.length === 0 && <div style={{ ...soft, marginTop: 22 }}>No completed analysis loaded for this résumé. Select the analyze button above to get feedback.</div>}
              </section>
            </div>
          </>}
        </div>
      </div>
    </>
  );
}

function FeedbackList({ value }) {
  if (Array.isArray(value)) {
    return (
      <ul>
        {value.map((item, index) => (
          <li key={String(item) + index}>{String(item)}</li>
        ))}
      </ul>
    );
  }

  if (value && typeof value === "object") {
    return (
      <ul>
        {Object.entries(value).map(([key, item]) => (
          <li key={key}>
            <strong>{displayLabel(key)}:</strong>{" "}
            {String(item)}
          </li>
        ))}
      </ul>
    );
  }

  return null;
}

// Readiness screen. Uses saved career goals and the existing readiness API.
// The primary résumé in the existing database is the shared active résumé.
// The backend restricts résumé analysis to that active résumé for each career.
function ReadinessView({ healthStatus, onBack, onOpen }) {
  const [goals, setGoals] = useState([]);
  const [paths, setPaths] = useState([]);
  const [results, setResults] = useState({});
  const [activeResume, setActiveResume] = useState(null);
  const [activeCareer, setActiveCareer] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const detailsRef = useRef(null);

  function viewCareerDetails(id) {
    setActiveCareer(id);
    // Wait until React renders the selected assessment before navigating to it.
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        detailsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  async function calculateGoals(careerGoals) {
    if (!careerGoals.length) return;
    setBusy(true);
    try {
      // Run sequentially to avoid competing writes on the same student account.
      const next = {};
      const failures = [];
      for (const goal of careerGoals) {
        const id = Number(goal.career_path_id);
        try {
          next[id] = await apiRequest("/students/me/readiness/calculate", {
            method: "POST",
            body: JSON.stringify({ career_path_id: id }),
          });
        } catch (error) {
          failures.push(`Career #${id}: ${error.message}`);
        }
      }
      setResults(next);
      setNotice(failures.length ? {
        type: "error",
        text: `Some readiness assessments could not be calculated. ${failures.join(" ")}`,
      } : null);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function initialize() {
      try {
        const [goalResponse, pathResponse, resumeResponse] = await Promise.all([
          apiRequest("/students/me/career-goals"),
          loadTigerPadCatalog("/career-paths"),
          apiRequest("/students/me/resumes"),
        ]);
        if (cancelled) return;
        const uniqueGoals = Array.from(new Map(
          asArray(goalResponse)
            .filter((goal) => goal.career_path_id &&
              !["inactive", "removed", "archived"].includes(String(goal.status || "").toLowerCase()))
            .map((goal) => [Number(goal.career_path_id), goal]),
        ).values());
        setGoals(uniqueGoals);
        setPaths(asArray(pathResponse));
        setActiveResume(asArray(resumeResponse).find((item) => item.is_primary) || null);
        setActiveCareer(uniqueGoals[0] ? String(uniqueGoals[0].career_path_id) : "");
        setLoading(false);
        if (uniqueGoals.length) await calculateGoals(uniqueGoals);
      } catch (error) {
        if (!cancelled) {
          setNotice({ type: "error", text: error.message });
          setLoading(false);
        }
      }
    }
    initialize();
    return () => { cancelled = true; };
  }, []);

  const careerName = (id) => paths.find((path) =>
    Number(path.career_path_id) === Number(id))?.name || `Career #${id}`;
  const score = results[activeCareer];
  const metrics = score ? [
    ["Academic preparation", score.academic_score],
    ["Skills", score.skill_score],
    ["Experience", score.experience_score],
    ["Projects", score.project_score],
    ["Certifications", score.certification_score],
    ["Résumé", score.resume_score],
  ] : [];
  const openGaps = (score?.skill_gaps || [])
    .filter((gap) => Number(gap.gap_size) > 0)
    .sort((a, b) => Number(b.priority_score) - Number(a.priority_score));
  const suggestions = [];
  if (score) {
    if (Number(score.skill_score) < 80) suggestions.push("Add and strengthen career-relevant skills in My Profile.");
    if (Number(score.experience_score) < 80) suggestions.push("Document additional relevant experience in My Profile.");
    if (Number(score.project_score) < 80) suggestions.push("Add completed projects and describe their outcomes.");
    if (Number(score.certification_score) < 80) suggestions.push("Record relevant certifications you have earned.");
    if (Number(score.resume_score) < 80) suggestions.push("Review your résumé and run its career-specific AI analysis in Résumé Studio.");
  }

  const safePercent = (value) => Math.max(0, Math.min(100, Number(value) || 0));
  const strongest = metrics.length ? [...metrics].sort((a,b) => Number(b[1] || 0) - Number(a[1] || 0))[0] : null;
  const actions = score ? [
    { label: "Improve your skills", description: "Add career-relevant skills and proficiency levels.", value: score.skill_score, page: "profile" },
    { label: "Document experience", description: "Record relevant work and responsibilities.", value: score.experience_score, page: "profile" },
    { label: "Show your projects", description: "Add projects and describe the results.", value: score.project_score, page: "profile" },
    { label: "Add certifications", description: "Record certifications you have completed.", value: score.certification_score, page: "profile" },
    { label: "Analyze your résumé", description: "Run a career-specific résumé analysis.", value: score.resume_score, page: "resume" },
  ].filter((action) => Number(action.value || 0) < 80).sort((a,b) => Number(a.value || 0) - Number(b.value || 0)) : [];
  return (
    <>
      <PageHeader onBack={onBack} />
      <div className="welcome-row">
        <div><p className="eyebrow">Career readiness</p><h1>Your readiness dashboard.</h1>
          <p className="dashboard-intro">Understand your progress and choose what to improve next.</p></div>
        <HealthPill healthStatus={healthStatus} />
      </div>
      <Notice notice={notice} />
      {loading ? <article className="dashboard-card"><p>Loading your career goals…</p></article> :
        goals.length === 0 ? <article className="dashboard-card"><h2>No career goals saved yet</h2><p>Save a career goal in Career Paths to start tracking your readiness.</p><button type="button" className="secondary-button" onClick={() => onOpen("careers")}>Explore career paths</button></article> :
        <div className="tp-readiness">
          <section className="tp-ready-toolbar dashboard-card">
            <div className="tp-ready-toolbar-main"><label htmlFor="tp-ready-career">Career goal</label>
              <select id="tp-ready-career" value={activeCareer} onChange={(e) => setActiveCareer(e.target.value)}>
                {goals.map((goal) => <option key={goal.career_path_id} value={String(goal.career_path_id)}>{careerName(goal.career_path_id)}</option>)}
              </select><p>Each career has its own readiness assessment.</p></div>
            <button type="button" className="secondary-button" disabled={busy} onClick={() => calculateGoals(goals)}>{busy ? "Calculating…" : "↻ Refresh scores"}</button>
          </section>
          {score ? <>
            <section className="tp-ready-summary">
              <article className="dashboard-card tp-ready-overall"><p className="card-label">Overall readiness</p>
                <div className="tp-ready-bigscore">{displayScore(score.overall_score)}%</div>
                <div className="tp-ready-track"><div style={{width:`${safePercent(score.overall_score)}%`}} /></div>
                <p>Measures recorded qualifications for <strong>{careerName(activeCareer)}</strong>, not your chance of getting hired.</p></article>
              <article className="dashboard-card tp-ready-overall"><p className="card-label">Your strongest area</p>
                <div className="tp-ready-bigscore">{strongest ? `${displayScore(strongest[1])}%` : "—"}</div>
                <h3>{strongest?.[0] || "No assessment yet"}</h3>
                <p>Build on this strength while improving other areas.</p></article>
              <article className="dashboard-card tp-ready-overall"><p className="card-label">Next priority</p>
                <h3 className="tp-ready-priority">{actions[0]?.label || "Keep your profile current"}</h3>
                <p>{actions[0]?.description || "Your readiness profile is looking good."}</p>
                {actions[0] && <button type="button" className="secondary-button" onClick={() => onOpen(actions[0].page)}>Go to {actions[0].page === "resume" ? "Résumé Studio" : "My Profile"} →</button>}
              </article>
            </section>
            <section className="tp-ready-columns">
              <article className="dashboard-card tp-ready-breakdown"><div className="tp-ready-heading"><div><p className="card-label">Your assessment</p><h2>Score breakdown</h2></div><span className="tp-ready-date">{score.calculated_at ? `Updated ${new Date(score.calculated_at).toLocaleDateString()}` : "Latest assessment"}</span></div>
                <p>See how each part of your profile contributes to career readiness.</p>
                <div className="tp-ready-metrics">{metrics.map(([label,value]) => <div className="tp-ready-metric" key={label}>
                  <div className="tp-ready-metric-top"><strong>{label}</strong><span>{displayScore(value)}%</span></div>
                  <div className="tp-ready-track"><div style={{width:`${safePercent(value)}%`}} /></div>
                </div>)}</div>
                <p className="tp-ready-note">A zero can mean missing profile evidence or, for the résumé category, no completed career-specific analysis of your active résumé.</p>
                <p className="tp-ready-note">Active résumé: <strong>{activeResume?.title || "None selected"}</strong>. Manage it in Résumé Studio.</p>
              </article>
              <article className="dashboard-card tp-ready-actions"><p className="card-label">Personalized action plan</p><h2>What to do next</h2>
                <p>Start with these lower-scoring areas. Each action opens the relevant TigerPad section.</p>
                <div className="tp-ready-action-list">{actions.length ? actions.map((action,index) => <div className="tp-ready-action" key={action.label}>
                  <span className="tp-ready-action-number">{index+1}</span><div><strong>{action.label}</strong><p>{action.description}</p><small>Current category score: {displayScore(action.value)}%</small></div>
                  <button type="button" className="tp-ready-action-button" onClick={() => onOpen(action.page)} aria-label={`Open ${action.page === "resume" ? "Résumé Studio" : "My Profile"} to ${action.label.toLowerCase()}`}>Open →</button>
                </div>) : <p>All tracked categories are at least 80%. Continue updating your accomplishments.</p>}</div>
              </article>
            </section>
            <article className="dashboard-card tp-ready-gaps"><div className="tp-ready-heading"><div><p className="card-label">Skills to develop</p><h2>Priority skill gaps</h2></div><span className="tp-ready-count">{openGaps.length} identified</span></div>
              {openGaps.length ? <div className="tp-ready-gap-list">{openGaps.map((gap,index) => <div className="tp-ready-gap" key={gap.skill_gap_id || index}>
                <span className="tp-ready-gap-rank">{index+1}</span><div><strong>{gap.recommend_action || `Improve target skill #${gap.career_path_skill_id}`}</strong>
                <p>Current proficiency: {gap.current_proficiency_level ?? "—"} · Target: {gap.target_proficiency_level ?? "—"}</p></div></div>)}</div> : <p>No outstanding skill gaps were returned for this career.</p>}
              <button type="button" className="secondary-button" onClick={() => onOpen("profile")}>Update skills in My Profile →</button>
            </article>
            <p className="tp-ready-disclaimer">Scores and suggested actions are based on TigerPad's existing readiness calculations and recorded student information. They are not new AI-generated recommendations.</p>
          </> : <article className="dashboard-card"><h2>Assessment unavailable</h2><p>{busy ? "Calculating your readiness…" : "We couldn't load this career's assessment. Try refreshing your scores."}</p></article>}
        </div>}
    </>
  );
}

// General behavioral interview workflow.
function InterviewsView({ healthStatus, onBack }) {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [response, setResponse] = useState(null);
  const [answer, setAnswer] = useState("");
  const [notice, setNotice] = useState(null);

  const [form, setForm] = useState({
    title: "General Career Behavioral Interview",
    interview_type: "behavioral",
    difficulty_level: "beginner",
    question_count: 5,
  });

  useEffect(() => {
    apiRequest("/students/me/interviews")
      .then((result) => setSessions(asArray(result)))
      .catch((error) =>
        setNotice({ type: "error", text: error.message }),
      );
  }, []);

  async function createSession(event) {
    event.preventDefault();

    try {
      const saved = await apiRequest(
        "/students/me/interviews",
        {
          method: "POST",
          body: JSON.stringify({
            ...form,
            question_count: Number(form.question_count),
            career_path_id: null,
            resume_id: null,
          }),
        },
      );

      setSessions((current) => [saved, ...current]);
      setSelected(saved);

      setNotice({
        type: "success",
        text: "Interview session created.",
      });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    }
  }

  async function startSession() {
    const result = await apiRequest(
      "/students/me/interviews/" +
        selected.interview_session_id +
        "/start",
      { method: "POST" },
    );

    setSelected(result);
  }

  async function generateQuestion() {
    const result = await apiRequest(
      "/students/me/interviews/" +
        selected.interview_session_id +
        "/generate-question",
      { method: "POST" },
    );

    setResponse(result);
    setAnswer("");
  }

  async function submitAnswer(event) {
    event.preventDefault();

    const result = await apiRequest(
      "/students/me/interviews/" +
        selected.interview_session_id +
        "/responses/" +
        response.interview_response_id,
      {
        method: "PATCH",
        body: JSON.stringify({
          student_response: answer,
          response_duration_seconds: 60,
        }),
      },
    );

    setResponse(result);
  }

  async function evaluate() {
    const result = await apiRequest(
      "/students/me/interviews/" +
        selected.interview_session_id +
        "/responses/" +
        response.interview_response_id +
        "/evaluate",
      { method: "POST" },
    );

    setResponse(result);
  }

  async function complete() {
    const result = await apiRequest(
      "/students/me/interviews/" +
        selected.interview_session_id +
        "/complete",
      { method: "POST" },
    );

    setSelected(result);

    setNotice({
      type: "success",
      text: "Interview completed.",
    });
  }

  return (
    <>
      <PageHeader onBack={onBack} />

      <div className="welcome-row">
        <div>
          <p className="eyebrow">Interview practice</p>
          <h1>Practice for your next opportunity.</h1>
          <p className="dashboard-intro">
            Use general behavioral questions that apply across majors
            and industries.
          </p>
        </div>

        <HealthPill healthStatus={healthStatus} />
      </div>

      <Notice notice={notice} />

      <div
        className="dashboard-grid"
        style={{ marginTop: "24px" }}
      >
        <article className="dashboard-card">
          <h2>Start an interview</h2>

          <form
            className="auth-form"
            onSubmit={createSession}
          >
            <label>
              Title
              <input
                value={form.title}
                onChange={(event) =>
                  setForm({
                    ...form,
                    title: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Difficulty
              <select
                value={form.difficulty_level}
                onChange={(event) =>
                  setForm({
                    ...form,
                    difficulty_level: event.target.value,
                  })
                }
                style={selectStyle}
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>

            <button className="primary-button">
              Create interview
            </button>
          </form>
        </article>

        <article className="dashboard-card">
          <h2>Previous sessions</h2>

          {sessions.map((item) => (
            <button
              type="button"
              className="text-button"
              key={item.interview_session_id}
              onClick={() => setSelected(item)}
              style={{
                display: "block",
                margin: "10px 0",
              }}
            >
              {item.title} · {displayLabel(item.status)}
            </button>
          ))}
        </article>
      </div>

      {selected && (
        <article
          className="dashboard-card"
          style={{ marginTop: "24px" }}
        >
          <h2>{selected.title}</h2>
          <p>Status: {displayLabel(selected.status)}</p>

          {selected.status === "created" && (
            <button
              type="button"
              className="secondary-button"
              onClick={startSession}
            >
              Start interview
            </button>
          )}

          {selected.status === "in_progress" && (
            <>
              <button
                type="button"
                className="secondary-button"
                onClick={generateQuestion}
              >
                Generate question
              </button>

              {response && (
                <div style={{ marginTop: "20px" }}>
                  <h3>{response.question_text}</h3>

                  <form
                    onSubmit={submitAnswer}
                    className="auth-form"
                  >
                    <textarea
                      value={answer}
                      onChange={(event) =>
                        setAnswer(event.target.value)
                      }
                      rows="6"
                      placeholder="Write your response..."
                      style={textareaStyle}
                      required
                    />

                    <button className="primary-button">
                      Submit response
                    </button>
                  </form>

                  {response.student_response && (
                    <>
                      <button
                        type="button"
                        className="text-button"
                        onClick={evaluate}
                      >
                        Evaluate response
                      </button>

                      <button
                        type="button"
                        className="text-button"
                        onClick={complete}
                      >
                        Complete interview
                      </button>
                    </>
                  )}

                  {response.feedback && (
                    <p>{response.feedback}</p>
                  )}
                </div>
              )}
            </>
          )}

          {selected.status === "completed" && (
            <p>
              Overall score:{" "}
              {displayScore(selected.overall_score)}
            </p>
          )}
        </article>
      )}
    </>
  );
}

// =============================================================================
// STUDENT NOTIFICATIONS AND FACULTY REVIEW FEEDBACK
// Uses only existing TigerPad backend endpoints; no additional files needed.
// =============================================================================
function StudentNotificationsView({ healthStatus, onBack, onUpdated }) {
  const [notifications, setNotifications] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [notice, setNotice] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.allSettled([
      apiRequest("/students/me/notifications?limit=100"),
      apiRequest("/students/me/profile/faculty-reviews?limit=100&offset=0"),
    ]).then(([notificationResult, reviewResult]) => {
      if (!active) return;
      if (notificationResult.status === "fulfilled") {
        setNotifications(asArray(notificationResult.value));
      } else {
        setNotice({ type: "error", text: notificationResult.reason.message });
      }
      if (reviewResult.status === "fulfilled") {
        const value = reviewResult.value;
        setReviews(Array.isArray(value?.reviews) ? value.reviews : asArray(value));
      } else {
        setNotice((current) => current || {
          type: "error",
          text: "Notifications loaded, but faculty review details are unavailable: " + reviewResult.reason.message,
        });
      }
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [refreshKey]);

  // Old notifications may contain an instruction to sign in. This page is
  // already authenticated, so remove only that redundant instruction from display.
  // Existing notification records are left unchanged in MySQL.
  function notificationText(message) {
    return String(message || "")
      .replace(/(?:please\s+)?sign\s+in\s+to\s+tigerpad\s+to\s+view\s+(?:it|this|your\s+feedback|the\s+feedback)[.!]?/gi, "")
      .replace(/(?:please\s+)?log\s+in\s+to\s+tigerpad\s+to\s+view\s+(?:it|this|your\s+feedback|the\s+feedback)[.!]?/gi, "")
      .replace(/\s{2,}/g, " ").trim();
  }

  function reviewFor(item) {
    if (item.related_entity_type !== "faculty_review") return null;
    return reviews.find((review) =>
      Number(review.review_id ?? review.faculty_review_id) === Number(item.related_entity_id)
    ) || null;
  }

  async function setRead(item, isRead) {
    setBusyId(item.notification_id);
    setNotice(null);
    try {
      const updated = await apiRequest(`/students/me/notifications/${item.notification_id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_read: isRead }),
      });
      setNotifications((current) => current.map((entry) =>
        entry.notification_id === item.notification_id
          ? { ...entry, ...updated, is_read: isRead }
          : entry
      ));
      onUpdated();
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusyId(null);
    }
  }

  async function openNotification(item) {
    setSelectedId(item.notification_id);
    if (!item.is_read) await setRead(item, true);
  }

  async function markAllRead() {
    setBusyId("all");
    setNotice(null);
    try {
      await apiRequest("/students/me/notifications/mark-all-read", { method: "POST" });
      setNotifications((current) => current.map((item) => ({
        ...item, is_read: true, read_at: item.read_at || new Date().toISOString(),
      })));
      onUpdated();
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusyId(null);
    }
  }

  const visible = notifications.filter((item) => !unreadOnly || !item.is_read);
  const unreadCount = notifications.filter((item) => !item.is_read).length;
  const selected = notifications.find((item) => item.notification_id === selectedId);
  const selectedReview = selected ? reviewFor(selected) : null;

  return (
    <>
      <PageHeader onBack={onBack} />
      <div className="welcome-row">
        <div>
          <p className="eyebrow">Student notification center</p>
          <h1>Your notifications.</h1>
          <p className="dashboard-intro">Select any notification to read its full details without signing in again.</p>
        </div>
        <HealthPill healthStatus={healthStatus} />
      </div>
      <Notice notice={notice} />
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", marginTop: 22, marginBottom: 18 }}>
        <button type="button" className="secondary-button" onClick={() => { setNotice(null); setRefreshKey((key) => key + 1); onUpdated(); }} disabled={loading}>Refresh</button>
        <button type="button" className="secondary-button" onClick={markAllRead} disabled={busyId !== null || unreadCount === 0}>Mark all read</button>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input type="checkbox" checked={unreadOnly} onChange={(event) => setUnreadOnly(event.target.checked)} />
          Unread only ({unreadCount})
        </label>
      </div>
      <section className="dashboard-card" style={{ marginTop: 16 }}>
        <p className="card-label">Notification inbox</p>
        <h2>{selected ? "Notification details" : "All notifications"}</h2>
        {selected ? (
          <div style={{ display: "grid", gap: 12 }}>
            <button type="button" className="text-button" style={{ justifySelf: "start" }} onClick={() => setSelectedId(null)}>← Back to notifications</button>
            <h3>{selected.title}</h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{notificationText(selected.message) || "You have a new TigerPad notification."}</p>
            <p><strong>Type:</strong> {displayLabel(selected.notification_type, "Notification")}</p>
            {selected.created_at && <p><strong>Received:</strong> {new Date(selected.created_at).toLocaleString()}</p>}
            {selected.related_entity_type === "faculty_review" && (
              <div style={{ borderTop: "1px solid #dce3ee", paddingTop: 16 }}>
                <h3>Faculty review details</h3>
                {selectedReview ? (
                  <>
                    <p><strong>Review type:</strong> {displayLabel(selectedReview.review_type)}</p>
                    <p><strong>Status:</strong> {displayLabel(selectedReview.status ?? selectedReview.review_status, "Submitted")}</p>
                    {selectedReview.overall_score != null && <p><strong>Score:</strong> {selectedReview.overall_score}/100</p>}
                    <p><strong>Overall feedback:</strong> {selectedReview.feedback || selectedReview.overall_feedback || selectedReview.comments || "No overall comments provided."}</p>
                    {selectedReview.strengths && <p><strong>Strengths:</strong> {selectedReview.strengths}</p>}
                    {selectedReview.areas_for_improvement && <p><strong>Areas for improvement:</strong> {selectedReview.areas_for_improvement}</p>}
                    {selectedReview.recommendations && <p><strong>Recommendations:</strong> {selectedReview.recommendations}</p>}
                  </>
                ) : (
                  <p>The review details are not available in the student review feed. The notification message is shown above.</p>
                )}
              </div>
            )}
            <button type="button" className="secondary-button" style={{ justifySelf: "start" }} disabled={busyId !== null} onClick={() => setRead(selected, !selected.is_read)}>
              {busyId === selected.notification_id ? "Updating..." : selected.is_read ? "Mark as unread" : "Mark as read"}
            </button>
          </div>
        ) : loading ? <p>Loading notifications...</p> : visible.length === 0 ? <p>No notifications to display.</p> : (
          <div style={{ display: "grid", gap: 12 }}>
            {visible.map((item) => (
              <button key={item.notification_id} type="button" onClick={() => openNotification(item)}
                style={{ width: "100%", textAlign: "left", cursor: "pointer", border: "1px solid #dce3ee", borderRadius: 12, padding: 16, color: "inherit", background: item.is_read ? "transparent" : "rgba(123,24,48,0.09)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <strong>{item.title}</strong><span>{item.is_read ? "Read" : "● Unread"}</span>
                </div>
                <p style={{ marginBottom: 6 }}>{notificationText(item.message) || "Open to view this notification."}</p>
                <span style={{ textDecoration: "underline" }}>View full notification →</span>
              </button>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

// Student progress center. Summarizes saved records without duplicating Notifications.
// All counts and scores come from existing TigerPad endpoints; this view does not
// create readiness assessments or alter the selected résumé.
function ActivityView({ healthStatus, onBack }) {
  // Progress is read-only except for choosing the active résumé. It never
  // recalculates readiness or creates new milestones when opened.
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [notice, setNotice] = useState(null);
  const [resumeBusy, setResumeBusy] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewError, setPreviewError] = useState("");
  const sources = [
    ["profile", "/students/me/profile"],
    ["summary", "/students/me/profile/summary"],
    ["goals", "/students/me/career-goals"],
    ["paths", "/career-paths"],
    ["scores", "/students/me/readiness"],
    ["resumes", "/students/me/resumes"],
    ["skills", "/students/me/skills"],
    ["projects", "/students/me/projects"],
    ["certifications", "/students/me/certifications"],
    ["experiences", "/students/me/experiences"],
    ["events", "/students/me/progress"],
  ];

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNotice(null);
    Promise.allSettled(sources.map(([, path]) => apiRequest(path)))
      .then((results) => {
        if (cancelled) return;
        const next = {};
        const unavailable = [];
        results.forEach((result, index) => {
          const name = sources[index][0];
          if (result.status === "fulfilled") next[name] = result.value;
          else unavailable.push(name);
        });
        setData(next);
        if (unavailable.length) {
          setNotice({ type: "error", text: `Some progress information could not be loaded: ${unavailable.join(", ")}. Refresh to try again.` });
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [refreshKey]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const list = (name) => asArray(data[name] ?? []);
  const goals = list("goals").filter((goal) => !["inactive", "removed", "archived"].includes(String(goal.status || "").toLowerCase()));
  const paths = list("paths");
  const scores = list("scores");
  const resumes = list("resumes");
  const activeResume = resumes.find((resume) => Boolean(resume.is_primary));
  const events = list("events");
  const profile = data.profile || {};
  const summary = data.summary || {};
  const checks = [
    ["Basic profile", Boolean(profile.preferred_name || profile.professional_headline || profile.bio)],
    ["Academic information", Boolean(profile.academic_level || profile.expected_graduation_date || profile.gpa != null)],
    ["Career goal", goals.length > 0],
    ["Skills", list("skills").length > 0],
    ["Experience", list("experiences").length > 0],
    ["Projects", list("projects").length > 0],
    ["Certifications", list("certifications").length > 0],
    ["Active résumé", Boolean(activeResume)],
  ];
  const completed = checks.filter(([, yes]) => yes).length;
  const completion = Math.round((completed / checks.length) * 100);
  const cardStyle = { marginTop: 0, minWidth: 0 };
  const soft = { padding: "14px 16px", border: "1px solid #304660", borderRadius: 12, marginTop: 12 };
  const progressBar = (value) => (
    <div style={{ height: 10, borderRadius: 12, background: "#23354b", overflow: "hidden", marginTop: 8 }}>
      <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, Number(value) || 0))}%`, background: "#28b6e8", borderRadius: 12 }} />
    </div>
  );
  const nextSteps = checks.filter(([, yes]) => !yes).map(([name]) => name);
  const dateLabel = (value) => {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString();
  };
  const goalScore = (goal) => scores
    .filter((score) => Number(score.career_path_id) === Number(goal.career_path_id))
    .sort((a, b) => Number(Boolean(b.is_current)) - Number(Boolean(a.is_current)) ||
      new Date(b.calculated_at || b.created_at || 0) - new Date(a.calculated_at || a.created_at || 0))[0];

  async function selectActiveResume(resumeId) {
    if (!resumeId) return;
    setResumeBusy(true);
    setNotice(null);
    setPreviewError("");
    setPreviewUrl(null);
    try {
      await apiRequest(`/students/me/resumes/${resumeId}`, {
        method: "PATCH", body: JSON.stringify({ is_primary: true }),
      });
      // Reload from the server so Progress and Résumé Studio agree on the selection.
      const updated = asArray(await apiRequest("/students/me/resumes"));
      setData((current) => ({ ...current, resumes: updated }));
      setNotice({ type: "success", text: "Active résumé updated. Readiness will use this résumé for future calculations." });
    } catch (error) {
      setNotice({ type: "error", text: `Could not select the résumé: ${error.message}` });
    } finally {
      setResumeBusy(false);
    }
  }

  async function previewActiveResume() {
    if (!activeResume) return;
    setResumeBusy(true);
    setPreviewError("");
    setPreviewUrl(null);
    try {
      if (activeResume.source_type !== "uploaded") {
        setPreviewError("This résumé was created in TigerPad. Open Résumé Studio to view its formatted draft.");
        return;
      }
      const blob = await _blobRequest(`/students/me/resumes/${activeResume.resume_id}/file`);
      const filename = String(activeResume.original_filename || activeResume.file_name || activeResume.title || "");
      const isPdf = blob.type.toLowerCase().includes("pdf") || /\.pdf$/i.test(filename);
      if (!isPdf) {
        setPreviewError("Inline preview is available for PDF résumés. Open Résumé Studio to view other document types.");
        return;
      }
      setPreviewUrl(URL.createObjectURL(blob));
    } catch (error) {
      setPreviewError(`Résumé preview is unavailable: ${error.message}`);
    } finally {
      setResumeBusy(false);
    }
  }

  return (
    <>
      <PageHeader onBack={onBack} />
      <div className="welcome-row">
        <div>
          <p className="eyebrow">Progress center</p>
          <h1>Your career journey.</h1>
          <p className="dashboard-intro">See your saved achievements, readiness assessments, and next steps in one place.</p>
        </div>
        <HealthPill healthStatus={healthStatus} />
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", margin: "12px 0 20px" }}>
        <button type="button" className="secondary-button" disabled={loading} onClick={() => setRefreshKey((value) => value + 1)}>
          {loading ? "Loading progress..." : "Refresh progress"}
        </button>
      </div>
      <Notice notice={notice} />
      {loading ? <article className="dashboard-card"><p>Loading your career progress...</p></article> : (
        <>
          <div className="dashboard-grid" style={{ marginTop: 20 }}>
            <article className="dashboard-card" style={cardStyle}>
              <p className="card-label">Career portfolio development</p>
              <h2>{data.profile ? `${completion}% of tracked steps` : "Unavailable"}</h2>
              <p>{data.profile ? `${completed} of ${checks.length} portfolio steps have saved information.` : "Profile details could not be loaded."}</p>
              {data.profile && progressBar(completion)}
              {data.summary !== undefined && <p style={{ marginTop: 12 }}>Basic profile status: <strong>{summary.is_profile_complete ? "Complete" : "In progress"}</strong></p>}
              <p style={{ fontSize: 13, opacity: 0.8 }}>Basic profile status and the eight-step portfolio checklist are separate. Neither is a career-readiness score.</p>
            </article>
            <article className="dashboard-card" style={cardStyle}>
              <p className="card-label">Your achievements</p>
              <h2>What you've recorded</h2>
              <div className="dashboard-grid" style={{ marginTop: 14 }}>
                {[["Skills", "skills"], ["Projects", "projects"], ["Certifications", "certifications"], ["Experiences", "experiences"]].map(([label, key]) => (
                  <div key={key} style={soft}>
                    <strong style={{ fontSize: 24 }}>{data[key] === undefined ? "—" : list(key).length}</strong>
                    <div>{label}</div>
                    {data[key] === undefined && <small>Could not load</small>}
                  </div>
                ))}
              </div>
              <p style={{ fontSize: 13, opacity: 0.8, marginTop: 12 }}>Counts reflect records saved in My Profile, not skills or experiences extracted from a résumé.</p>
            </article>
          </div>
          <div className="dashboard-grid" style={{ marginTop: 20 }}>
            <article className="dashboard-card" style={cardStyle}>
              <p className="card-label">Career goals</p>
              <h2>Readiness by career</h2>
              {data.goals === undefined || data.scores === undefined ? <p>Career readiness information is unavailable.</p> : goals.length === 0 ? <p>No career goals saved yet. Add one in Career Paths to start tracking readiness.</p> : goals.map((goal) => {
                const score = goalScore(goal);
                const path = paths.find((item) => Number(item.career_path_id) === Number(goal.career_path_id));
                const value = score?.overall_score;
                return <div key={goal.career_goal_id || goal.career_path_id} style={soft}>
                  <strong>{path?.name || goal.career_path_name || `Career #${goal.career_path_id}`}</strong>
                  <p style={{ margin: "6px 0" }}>{value == null ? "No readiness score recorded" : `${displayScore(value)}% readiness`}</p>
                  {value != null && progressBar(value)}
                  {score && <small style={{ opacity: 0.8 }}>Last assessed: {dateLabel(score.calculated_at || score.created_at) || "Date unavailable"}</small>}
                </div>;
              })}
              <p style={{ fontSize: 13, opacity: 0.8, marginTop: 14 }}>These are saved assessments. Open Readiness to calculate updated scores.</p>
            </article>
            <article className="dashboard-card" style={cardStyle}>
              <p className="card-label">Résumé development</p>
              <h2>Selected résumé</h2>
              {data.resumes === undefined ? <p>Résumé information is unavailable.</p> : resumes.length === 0 ? (
                <p>No résumés saved yet. Create or upload one in Résumé Studio.</p>
              ) : (
                <>
                  <label style={{ display: "block", marginTop: 12, fontWeight: 700 }} htmlFor="progress-active-resume">Choose the résumé used by Readiness</label>
                  <select id="progress-active-resume" value={activeResume?.resume_id || ""}
                    disabled={resumeBusy} onChange={(event) => selectActiveResume(event.target.value)}
                    style={{ ...selectStyle, background: "#0b2340", color: "#f1f7ff", border: "1px solid #416587", marginTop: 8 }}>
                    <option value="">Select an active résumé</option>
                    {resumes.map((resume) => <option key={resume.resume_id} value={resume.resume_id}>{resume.title || resume.original_filename || `Résumé #${resume.resume_id}`}</option>)}
                  </select>
                  {activeResume ? (
                    <div style={soft}>
                      <strong style={{ overflowWrap: "anywhere" }}>{activeResume.title || activeResume.original_filename || `Résumé #${activeResume.resume_id}`}</strong>
                      <p style={{ margin: "8px 0" }}>Active résumé · {displayLabel(activeResume.resume_type, "General")} · {activeResume.source_type === "uploaded" ? "Uploaded" : "Created in TigerPad"}</p>
                      {activeResume.original_filename && <p style={{ overflowWrap: "anywhere", margin: "6px 0" }}>File: {activeResume.original_filename}</p>}
                      <p>{resumes.length} résumé{resumes.length === 1 ? "" : "s"} in your library</p>
                      <button type="button" className="secondary-button" disabled={resumeBusy} onClick={previewActiveResume}>
                        {resumeBusy ? "Loading résumé..." : "Preview selected résumé"}
                      </button>
                    </div>
                  ) : <p style={{ marginTop: 12 }}>You have saved résumés, but none is marked active. Choose one above to synchronize it with Readiness.</p>}
                  {previewError && <p role="status" style={{ marginTop: 12 }}>{previewError}</p>}
                  {previewUrl && activeResume && <div style={{ marginTop: 16 }}>
                    <p style={{ fontWeight: 700 }}>PDF preview — {activeResume.title || "Active résumé"}</p>
                    <iframe title="Active résumé PDF preview" src={previewUrl} style={{ width: "100%", height: 440, border: "1px solid #416587", borderRadius: 10, background: "white" }} />
                    <p><a href={previewUrl} target="_blank" rel="noopener noreferrer" style={{ color: "#9ddfff" }}>Open PDF in a new tab</a></p>
                  </div>}
                </>
              )}
            </article>
          </div>
          <div className="dashboard-grid" style={{ marginTop: 20 }}>
            <article className="dashboard-card" style={cardStyle}>
              <p className="card-label">Next steps</p>
              <h2>Keep moving forward</h2>
              {data.profile === undefined ? <p>Profile steps are unavailable.</p> : nextSteps.length === 0 ? <p>All tracked portfolio steps have saved information. Keep your records current and revisit Readiness.</p> : (
                <ul style={{ paddingLeft: 22 }}>
                  {nextSteps.slice(0, 6).map((name) => <li key={name} style={{ marginBottom: 10 }}>Add or update: <strong>{name}</strong></li>)}
                </ul>
              )}
            </article>
            <article className="dashboard-card" style={cardStyle}>
              <p className="card-label">Recent milestones</p>
              <h2>Progress history</h2>
              {data.events === undefined ? <p>Progress history is unavailable.</p> : events.length === 0 ? <p>No recorded milestones yet.</p> : (
                <div style={{ maxHeight: 420, overflowY: "auto" }}>
                  {events.slice(0, 20).map((event, index) => (
                    <div key={event.progress_event_id || index} style={soft}>
                      <strong>{event.title || "Progress milestone"}</strong>
                      {event.description && <p style={{ margin: "6px 0" }}>{event.description}</p>}
                      <small style={{ opacity: 0.75 }}>{dateLabel(event.completed_at || event.occurred_at || event.created_at)}</small>
                    </div>
                  ))}
                </div>
              )}
            </article>
          </div>
        </>
      )}
    </>
  );
}

function ResourcesView({ healthStatus, onBack }) {
  const [resources, setResources] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState(null);
  const guides = [
    { resource_id: "guide-resume", resource_type: "resume", title: "Résumé preparation", description: "Use clear headings, highlight measurable accomplishments, and tailor skills and projects to your intended career direction.", provider_name: "TigerPad career-readiness guide" },
    { resource_id: "guide-interview", resource_type: "interview", title: "Interview preparation", description: "Practice behavioral responses using Situation, Task, Action, and Result (STAR). Prepare examples from courses, internships, and projects.", provider_name: "TigerPad career-readiness guide" },
    { resource_id: "guide-career", resource_type: "career exploration", title: "Explore career paths", description: "Compare career directions with your interests, academic program, existing skills, and professional goals.", provider_name: "TigerPad career-readiness guide" },
    { resource_id: "guide-cert", resource_type: "certifications", title: "Certifications and skills", description: "Identify relevant industry credentials and document hands-on evidence of your technical and professional skills.", provider_name: "TigerPad career-readiness guide" },
  ];
  useEffect(() => {
    let active = true;
    apiRequest("/resources")
      .then((result) => { if (active) setResources(asArray(result)); })
      .catch((error) => { if (active) setNotice({ type: "error", text: "Database resources could not be loaded (GET /api/resources): " + error.message + ". The built-in guides below are still available. Check the Resources API route and backend logs." }); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  const combined = [...resources, ...guides];
  const visible = combined.filter((item) =>
    (String(item.title || "") + " " + String(item.description || "") + " " + String(item.resource_type || ""))
      .toLowerCase().includes(search.toLowerCase()));
  return (
    <>
      <PageHeader onBack={onBack} />
      <div className="welcome-row"><div><p className="eyebrow">Career resources</p><h1>Find support.</h1><p className="dashboard-intro">Career-readiness guidance for JSU students and faculty.</p></div><HealthPill healthStatus={healthStatus} /></div>
      <Notice notice={notice} />
      {loading && <p>Loading resources...</p>}
      <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search career resources" style={{ ...selectStyle, marginTop: 20 }} />
      <div className="dashboard-grid" style={{ marginTop: 24 }}>
        {visible.map((item) => <article className="dashboard-card" key={item.resource_id || item.title}>
          <p className="card-label">{displayLabel(item.resource_type, "Career resource")}</p><h2>{item.title}</h2><p>{item.description}</p><p><strong>Provider:</strong> {item.provider_name || "TigerPad"}</p>
          {item.resource_url && /^https:\/\//i.test(item.resource_url) && <a href={item.resource_url} target="_blank" rel="noopener noreferrer">Open resource</a>}
        </article>)}
      </div>
      {!visible.length && <p>No resources match your search.</p>}
    </>
  );
}

// Faculty can update their own profile. Student review feedback is submitted through the dedicated review API.
function FacultyProfileEditor({ profile, onSaved }) {
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(null);
  useEffect(() => {
    setForm({
      department_id: profile?.department_id ?? "",
      job_title: profile?.job_title || "",
      office_location: profile?.office_location || "",
      phone_number: profile?.phone_number || "",
      bio: profile?.bio || "",
      linkedin_url: profile?.linkedin_url || "",
    });
  }, [profile]);

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      const payload = {
        department_id: form.department_id === "" ? null : Number(form.department_id),
        job_title: form.job_title || null,
        office_location: form.office_location || null,
        phone_number: form.phone_number || null,
        bio: form.bio || null,
        linkedin_url: form.linkedin_url || null,
      };
      const result = await apiRequest("/faculty/me/profile", {
        method: profile ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      onSaved(result);
      setNotice({ type: "success", text: "Faculty profile saved." });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="dashboard-card" style={{ marginTop: "24px" }}>
      <p className="card-label">Faculty profile management</p>
      <h2>Edit my faculty profile</h2>
      <p>Update your professional information. Program access and review permissions are managed by administrators.</p>
      <Notice notice={notice} />
      <form className="auth-form" onSubmit={save}>
        <div className="form-row">
          <label>Department ID
            <input type="number" min="1" value={form.department_id ?? ""} onChange={(event) => setForm((prev) => ({ ...prev, department_id: event.target.value }))} />
          </label>
          <label>Job title
            <input maxLength={100} value={form.job_title || ""} onChange={(event) => setForm((prev) => ({ ...prev, job_title: event.target.value }))} />
          </label>
        </div>
        <div className="form-row">
          <label>Office location
            <input maxLength={100} value={form.office_location || ""} onChange={(event) => setForm((prev) => ({ ...prev, office_location: event.target.value }))} />
          </label>
          <label>Phone number
            <input maxLength={25} value={form.phone_number || ""} onChange={(event) => setForm((prev) => ({ ...prev, phone_number: event.target.value }))} />
          </label>
        </div>
        <label>LinkedIn URL
          <input type="url" maxLength={500} value={form.linkedin_url || ""} onChange={(event) => setForm((prev) => ({ ...prev, linkedin_url: event.target.value }))} />
        </label>
        <label>Bio
          <textarea style={textareaStyle} rows={4} maxLength={10000} value={form.bio || ""} onChange={(event) => setForm((prev) => ({ ...prev, bio: event.target.value }))} />
        </label>
        <button type="submit" className="secondary-button" disabled={saving}>{saving ? "Saving..." : "Save faculty profile"}</button>
      </form>
    </article>
  );
}

// Dedicated faculty profile page; kept separate from the student review workspace.
function facultyProgramName(item, programs) {
  const program = programs.find((entry) =>
    Number(entry.program_id) === Number(item.program_id)
  );
  return program?.name || item.program_name || `Program #${item.program_id}`;
}

function FacultyProfileView({ healthStatus, onBack }) {
  const [profile, setProfile] = useState(null);
  const [access, setAccess] = useState([]);
  const [programCatalog, setProgramCatalog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      apiRequest("/faculty/me/profile"),
      apiRequest("/faculty/me/program-access"),
      loadTigerPadCatalog("/academic-programs"),
    ]).then(([profileResult, accessResult, catalogResult]) => {
      if (!active) return;
      if (profileResult.status === "fulfilled") setProfile(profileResult.value);
      else if (profileResult.reason?.status !== 404) {
        setNotice({ type: "error", text: "Could not load faculty profile: " + profileResult.reason?.message });
      }
      if (accessResult.status === "fulfilled") setAccess(asArray(accessResult.value));
      else setNotice({ type: "error", text: "Could not load program access: " + accessResult.reason?.message });
      if (catalogResult.status === "fulfilled") setProgramCatalog(asArray(catalogResult.value));
      setLoading(false);
    });
    return () => { active = false; };
  }, []);

  return <>
    <PageHeader onBack={onBack} />
    <div className="welcome-row">
      <div><p className="eyebrow">Faculty profile</p><h1>Manage your faculty profile.</h1>
        <p className="dashboard-intro">Update your information and view authorized academic programs. Student reviews are managed in their own tab.</p>
      </div><HealthPill healthStatus={healthStatus} />
    </div>
    <Notice notice={notice} />
    {loading ? <p>Loading faculty profile...</p> : <>
      <FacultyProfileEditor profile={profile} onSaved={setProfile} />
      <article className="dashboard-card" style={{ marginTop: 24 }}>
        <p className="card-label">Program permissions</p><h2>Authorized programs</h2>
        {access.length ? <ul>{access.map((item) =>
          <li key={item.faculty_program_access_id || item.program_id}>
            {facultyProgramName(item, programCatalog)} · {displayLabel(item.access_level)} · {item.is_active ? "Active" : "Inactive"}
          </li>)}</ul> : <p>No program access records.</p>}
        <p>Program access and review permissions are managed by administrators.</p>
      </article>
    </>}
  </>;
}

// Faculty dashboard: overview and navigation, separate from the Faculty workspace.
function FacultyDashboardView({ healthStatus, onOpen, navigation = [] }) {
  const [profile, setProfile] = useState(null);
  const [access, setAccess] = useState([]);
  const [students, setStudents] = useState([]);
  const [notice, setNotice] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      apiRequest("/faculty/me/profile"),
      apiRequest("/faculty/me/program-access"),
      apiRequest("/faculty/students?limit=100"),
    ]).then((results) => {
      if (cancelled) return;
      if (results[0].status === "fulfilled") setProfile(results[0].value);
      if (results[1].status === "fulfilled") setAccess(asArray(results[1].value));
      if (results[2].status === "fulfilled") setStudents(asArray(results[2].value));
      if (results[2].status === "rejected") {
        setNotice({ type: "error", text: results[2].reason?.message || "Student access is unavailable." });
      }
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  const activeAccess = access.filter((item) => item.is_active &&
    (!item.expires_at || new Date(item.expires_at) > new Date()));
  return (
    <>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">Faculty dashboard</p>
          <h1>Welcome to your faculty dashboard.</h1>
          <p className="dashboard-intro">Monitor student readiness and open your advising workspace.</p>
        </div>
        <HealthPill healthStatus={healthStatus} />
      </div>
      <QuickTabs navigation={navigation} onOpen={onOpen} />
      <Notice notice={notice} />
      <div className="dashboard-grid" style={{ marginTop: "24px" }}>
        <article className="dashboard-card">
          <p className="card-label">Students</p>
          <h2>{loading ? "Loading..." : students.length}</h2>
          <p>Authorized student profiles loaded (up to 100).</p>
          <button type="button" className="secondary-button" onClick={() => onOpen("faculty")}>Open student management</button>
        </article>
        <article className="dashboard-card">
          <p className="card-label">Program access</p>
          <h2>{loading ? "Loading..." : activeAccess.length}</h2>
          <p>Active academic-program assignments.</p>
          <button type="button" className="text-button" onClick={() => onOpen("faculty-profile")}>View permissions</button>
        </article>
        <article className="dashboard-card">
          <p className="card-label">Faculty account</p>
          <h2>{profile?.job_title || "Faculty profile"}</h2>
          <p>{profile?.can_review_students ? "Student review permission enabled" : "Review permission requires administrator approval"}</p>
          <button type="button" className="text-button" onClick={() => onOpen("faculty-profile")}>Manage my profile</button>
        </article>
      </div>
    </>
  );
}

// Faculty view.
// Faculty review editor uses the existing protected faculty review API.
// A selected student is required; authorization is enforced by FastAPI.
function FacultyStudentReviews({ student, canReview }) {
  const studentId = student?.student_profile_id;
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const blank = { review_type: "resume", status: "completed", feedback: "", strengths: "", areas_for_improvement: "", recommendations: "" };
  const [form, setForm] = useState(blank);
  async function reload() {
    if (!studentId) return;
    setLoading(true);
    try {
      const result = await apiRequest(`/faculty/students/${studentId}/reviews`);
      setReviews(asArray(result));
    } catch (error) { setNotice({ type: "error", text: "Could not load review history: " + error.message }); }
    finally { setLoading(false); }
  }
  useEffect(() => {
    setReviews([]); setForm(blank); setEditingId(null); setNotice(null);
    reload();
  }, [studentId]);
  function change(event) { const { name, value } = event.target; setForm((current) => ({ ...current, [name]: value })); }
  async function submit(event) {
    event.preventDefault();
    if (!studentId || !canReview) return;
    setSaving(true); setNotice(null);
    try {
      const payload = { ...form, ...(editingId ? {} : { student_profile_id: Number(studentId) }) };
      await apiRequest(editingId ? `/faculty/reviews/${editingId}` : "/faculty/reviews", {
        method: editingId ? "PATCH" : "POST", body: JSON.stringify(payload),
      });
      setNotice({ type: "success", text: editingId ? "Review updated." : "Review submitted. The student notification will be handled by the backend." });
      setEditingId(null); setForm(blank); await reload();
    } catch (error) { setNotice({ type: "error", text: "Review could not be saved: " + error.message }); }
    finally { setSaving(false); }
  }
  function edit(review) {
    setEditingId(review.review_id);
    setForm({
      review_type: review.review_type || "resume", status: review.status || "completed",
      feedback: review.feedback || "", strengths: review.strengths || "",
      areas_for_improvement: review.areas_for_improvement || "",
      recommendations: review.recommendations || "",
    });
    setNotice(null);
  }
  return <section className="dashboard-card" style={{ marginTop: 24 }}>
    <p className="card-label">Faculty feedback</p><h2>Student reviews</h2>
    <p>Write feedback for this authorized student and review previous submissions.</p>
    <Notice notice={notice} />
    {!canReview && <p>Review submission requires faculty review permission. Contact an administrator if this access is expected.</p>}
    <form className="auth-form" onSubmit={submit}>
      <div className="form-row">
        <label>Review type<select name="review_type" value={form.review_type} onChange={change} style={selectStyle} required>{[["resume", "Résumé"], ["skills", "Skills"], ["projects", "Projects"], ["certifications", "Certifications"], ["career_readiness", "Career readiness"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label>Status<select name="status" value={form.status} onChange={change} style={selectStyle}><option value="completed">Completed</option><option value="draft">Draft</option><option value="in_progress">In progress</option></select></label>
      </div>
      {[ ["feedback", "Overall feedback"], ["strengths", "Strengths"], ["areas_for_improvement", "Areas for improvement"], ["recommendations", "Recommendations"] ].map(([name, label]) =>
        <label key={name}>{label}<textarea name={name} value={form[name]} onChange={change} rows={3} style={textareaStyle} required={name === "feedback"} /></label>
      )}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button className="secondary-button" type="submit" disabled={saving || !canReview}>{saving ? "Saving..." : editingId ? "Update review" : "Submit review"}</button>
        {editingId && <button type="button" className="text-button" onClick={() => { setEditingId(null); setForm(blank); }}>Cancel editing</button>}
      </div>
    </form>
    <h3 style={{ marginTop: 24 }}>Review history</h3>
    {loading && <p>Loading reviews...</p>}
    {!loading && reviews.length === 0 && <p>No reviews have been submitted for this student.</p>}
    {reviews.map((review) => <div key={review.review_id} style={{ borderTop: "1px solid #dce3ee", padding: "16px 0" }}>
      <strong>{displayLabel(review.review_type, "Faculty review")}</strong> · {displayLabel(review.status, "Submitted")}
      <p>{review.feedback || review.overall_feedback || review.comments || "No overall feedback provided."}</p>
      {review.strengths && <p><strong>Strengths:</strong> {review.strengths}</p>}
      {review.areas_for_improvement && <p><strong>Areas for improvement:</strong> {review.areas_for_improvement}</p>}
      {review.recommendations && <p><strong>Recommendations:</strong> {review.recommendations}</p>}
      {canReview && <button type="button" className="text-button" onClick={() => edit(review)}>Edit review</button>}
    </div>)}
  </section>;
}

function FacultyView({
  facultyUserId,
  healthStatus,
  onBack,
  onOpen,
  navigation = [],
  showPageHeader = true,
}) {
  const [students, setStudents] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [recentStudents, setRecentStudents] = useState([]);
  const recentKey = `tigerpad_faculty_recent_students_${facultyUserId}`;
  const [profile, setProfile] = useState(null);
  const [access, setAccess] = useState([]);
  const [programCatalog, setProgramCatalog] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [filters, setFilters] = useState({
    search_text: "",
    academic_level: "",
    program_id: "",
    is_profile_complete: "",
  });
  const [notice, setNotice] = useState(null);
  const [loadingStudents, setLoadingStudents] = useState(false);

  async function loadStudents(nextFilters = filters) {
    setLoadingStudents(true);
    try {
      const params = new URLSearchParams();
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value !== "" && value !== null && value !== undefined) {
          params.set(key, value);
        }
      });

      const suffix = params.toString() ? "?" + params.toString() : "";
      const result = await apiRequest("/faculty/students" + suffix);
      setStudents(asArray(result));
      setHasSearched(true);
      setSelectedStudent(null);
      setNotice(null);
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setLoadingStudents(false);
    }
  }

  useEffect(() => {
    Promise.allSettled([
      apiRequest("/faculty/me/profile"),
      apiRequest("/faculty/me/program-access"),
      loadTigerPadCatalog("/academic-programs"),
    ]).then(async (results) => {
      const value = (index) =>
        results[index].status === "fulfilled"
          ? results[index].value
          : null;

      setProfile(value(0));
      setAccess(asArray(value(1)));
      setProgramCatalog(asArray(value(2)));
      // Do not show an unfiltered student list before the faculty member searches.
    });
  }, []);

  useEffect(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem(recentKey) || "[]");
      setRecentStudents(Array.isArray(stored) ? stored.slice(0, 5) : []);
    } catch {
      setRecentStudents([]);
    }
  }, [recentKey]);

  function clearRecentStudents() {
    sessionStorage.removeItem(recentKey);
    setRecentStudents([]);
  }

  function updateFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }

  async function viewStudent(student) {
    try {
      const detail = await apiRequest(
        "/faculty/students/" + student.student_profile_id,
      );
      setSelectedStudent(detail);
      setNotice(null);
      const entry = {
        student_profile_id: detail.student_profile_id,
        first_name: detail.first_name,
        last_name: detail.last_name,
        academic_level: detail.academic_level,
        programs: asArray(detail.programs).map((program) => program.name).filter(Boolean),
      };
      setRecentStudents((previous) => {
        const updated = [entry, ...previous.filter((item) =>
          Number(item.student_profile_id) !== Number(entry.student_profile_id)
        )].slice(0, 5);
        try { sessionStorage.setItem(recentKey, JSON.stringify(updated)); } catch { /* Storage may be unavailable. */ }
        return updated;
      });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    }
  }

  return (
    <>
      {showPageHeader && <PageHeader onBack={onBack} />}

      <div className="welcome-row">
        <div>
          <p className="eyebrow">Student reviews</p>
          <h1>Review authorized students.</h1>
          <p className="dashboard-intro">
            Review only the student profiles and programs assigned to you.
          </p>
        </div>
        <HealthPill healthStatus={healthStatus} />
      </div>

      {onOpen && <QuickTabs navigation={navigation} onOpen={onOpen} />}
      <Notice notice={notice} />

      <div className="dashboard-grid" style={{ marginTop: "24px" }}>
        <article className="dashboard-card">
          <p className="card-label">Faculty profile</p>
          <h2>{profile?.job_title || "Faculty profile"}</h2>
          <p>
            {profile?.can_review_students
              ? "Student review access is enabled."
              : "Student review access is awaiting administrator approval."}
          </p>
        </article>

        <article className="dashboard-card">
          <p className="card-label">Authorized programs</p>
          <h2>{access.length}</h2>
          {access.length ? (
            <ul>
              {access.map((item) => (
                <li key={item.faculty_program_access_id}>
                  {facultyProgramName(item, programCatalog)} · {displayLabel(item.access_level)}
                </li>
              ))}
            </ul>
          ) : (
            <p>No program access records.</p>
          )}
        </article>
      </div>

      <article className="dashboard-card" style={{ marginTop: "24px" }}>
        <p className="card-label">Authorized student review</p>
        <h2>Find students</h2>

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            loadStudents(filters);
          }}
        >
          <div className="form-row">
            <label>
              Search
              <input
                name="search_text"
                value={filters.search_text}
                onChange={updateFilter}
                placeholder="Name, email, or headline"
              />
            </label>

            <label>
              Program
              <select
                name="program_id"
                value={filters.program_id}
                onChange={updateFilter}
                style={selectStyle}
              >
                <option value="">All authorized programs</option>
                {access.map((item) => (
                  <option
                    key={item.program_id}
                    value={item.program_id}
                  >
                    {facultyProgramName(item, programCatalog)}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Academic level
              <select
                name="academic_level"
                value={filters.academic_level}
                onChange={updateFilter}
                style={selectStyle}
              >
                <option value="">All levels</option>
                <option value="freshman">Freshman</option>
                <option value="sophomore">Sophomore</option>
                <option value="junior">Junior</option>
                <option value="senior">Senior</option>
                <option value="graduate">Graduate</option>
              </select>
            </label>

            <label>
              Profile status
              <select
                name="is_profile_complete"
                value={filters.is_profile_complete}
                onChange={updateFilter}
                style={selectStyle}
              >
                <option value="">All profiles</option>
                <option value="true">Complete</option>
                <option value="false">In progress</option>
              </select>
            </label>
          </div>

          <button className="secondary-button" type="submit">
            {loadingStudents ? "Searching..." : "Search students"}
          </button>
        </form>

        {!hasSearched ? (
          <p style={{ marginTop: "18px" }}>Use the search above to find students in your authorized programs. Results will appear here.</p>
        ) : students.length ? (
          <div style={{ marginTop: "20px" }}>
            {students.map((student) => (
              <div
                key={student.student_profile_id}
                style={{
                  borderTop: "1px solid #dce3ee",
                  padding: "14px 0",
                }}
              >
                <strong>
                  {student.first_name} {student.last_name}
                </strong>
                <p>
                  {displayLabel(student.academic_level, "Level not added")} ·{" "}
                  {student.is_profile_complete ? "Complete profile" : "In progress"}
                </p>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => viewStudent(student)}
                >
                  View permitted details →
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ marginTop: "18px" }}>
            No students matched your search and filters. Try another name or broaden your filters.
          </p>
        )}
      </article>

      <article className="dashboard-card" style={{ marginTop: "24px" }}>
        <div className="card-heading-row">
          <div>
            <p className="card-label">Faculty history</p>
            <h2>Recently viewed students</h2>
            <p>Quickly reopen a student you have viewed during this browser session.</p>
          </div>
          {recentStudents.length > 0 && (
            <button type="button" className="text-button" onClick={clearRecentStudents}>Clear history</button>
          )}
        </div>
        {recentStudents.length ? recentStudents.map((student) => (
          <div key={student.student_profile_id} style={{ borderTop: "1px solid #315575", padding: "14px 0" }}>
            <strong>{student.first_name} {student.last_name}</strong>
            <p>{displayLabel(student.academic_level, "Level not added")}{student.programs?.length ? ` · ${student.programs.join(", ")}` : ""}</p>
            <button type="button" className="text-button" onClick={() => viewStudent(student)}>
              View permitted details →
            </button>
          </div>
        )) : <p>No recently viewed students yet. Open a student from search results to add them here.</p>}
        <p style={{ fontSize: "0.85rem", opacity: 0.75 }}>
          Recent history is stored only in this browser session. TigerPad checks your current permissions every time you reopen a student.
        </p>
      </article>

      {selectedStudent && (
        <article className="dashboard-card" style={{ marginTop: "24px" }}>
          <div className="card-heading-row">
            <div>
              <p className="card-label">Authorized student profile</p>
              <h2>
                {selectedStudent.preferred_name || selectedStudent.first_name}{" "}
                {selectedStudent.last_name}
              </h2>
            </div>
            <button
              type="button"
              className="text-button"
              onClick={() => setSelectedStudent(null)}
            >
              Close
            </button>
          </div>

          <p>{selectedStudent.professional_headline || "No headline added."}</p>
          <p>{selectedStudent.bio || "No biography added."}</p>
          <p>
            <strong>Academic level:</strong>{" "}
            {displayLabel(selectedStudent.academic_level, "Not added")}
            {selectedStudent.gpa ? " · GPA " + selectedStudent.gpa : ""}
          </p>

          <div className="dashboard-grid" style={{ marginTop: "18px" }}>
            <div>
              <h3>Programs</h3>
              <ul>
                {asArray(selectedStudent.programs).map((item) => (
                  <li key={item.student_program_id}>
                    {item.name} {item.is_primary ? "(primary)" : ""}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Skills</h3>
              <ul>
                {asArray(selectedStudent.skills).map((item) => (
                  <li key={item.student_skill_id}>
                    {item.name} · level {item.proficiency_level}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <h3>Experience and projects</h3>
          <ul>
            {asArray(selectedStudent.experiences).map((item) => (
              <li key={item.experience_id}>
                {item.position_title} · {item.organization_name}
              </li>
            ))}
            {asArray(selectedStudent.projects).map((item) => (
              <li key={item.project_id}>
                {item.title} · {item.role_title || "Project"}
              </li>
            ))}
          </ul>

          <h3>Certifications</h3>
          <ul>
            {asArray(selectedStudent.certifications).map((item) => (
              <li key={item.certification_id}>
                {item.name} · {item.issuing_organization}
              </li>
            ))}
          </ul>
          <FacultyStudentReviews student={selectedStudent} canReview={Boolean(profile?.can_review_students)} />
        </article>
      )}
    </>
  );
}

// Administrator view.

// Administrator-only career path content management.
function AdminCareerPathManager({ onChanged }) {
  const emptyForm = { industry_id: "", name: "", career_path_code: "", description: "", typical_education_level: "" };
  const [industries, setIndustries] = useState([]);
  const [paths, setPaths] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [filter, setFilter] = useState("all");

  async function reload() {
    const [industryResult, pathResult] = await Promise.all([
      apiRequest("/admin/industries"),
      apiRequest("/admin/career-paths"),
    ]);
    setIndustries(asArray(industryResult));
    setPaths(asArray(pathResult));
  }

  useEffect(() => {
    reload().catch((error) => setNotice({ type: "error", text: error.message }));
  }, []);

  function startEdit(path) {
    setEditingId(path.career_path_id);
    setForm({
      industry_id: String(path.industry_id),
      name: path.name || "",
      career_path_code: path.career_path_code || "",
      description: path.description || "",
      typical_education_level: path.typical_education_level || "",
    });
    setNotice(null);
  }

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setNotice(null);
    try {
      const payload = { ...form, industry_id: Number(form.industry_id),
        description: form.description.trim() || null,
        typical_education_level: form.typical_education_level.trim() || null };
      await apiRequest(editingId ? "/admin/career-paths/" + editingId : "/admin/career-paths", {
        method: editingId ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      await reload();
      if (onChanged) await onChanged();
      setNotice({ type: "success", text: editingId ? "Career path updated." : "Career path saved as a private draft." });
      setEditingId(null);
      setForm(emptyForm);
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function setPublished(path) {
    setBusy(true);
    setNotice(null);
    try {
      await apiRequest("/admin/career-paths/" + path.career_path_id + "/publication", {
        method: "PATCH",
        body: JSON.stringify({ is_active: !path.is_active }),
      });
      await reload();
      if (onChanged) await onChanged();
      setNotice({ type: "success", text: path.is_active ? "Career path unpublished." : "Career path published for students and faculty." });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  const shown = paths.filter((path) => filter === "all" || (filter === "published" ? path.is_active : !path.is_active));
  return (
    <article className="dashboard-card" style={{ marginTop: "24px" }}>
      <p className="card-label">Administrator content management</p>
      <h2>Career Path Management</h2>
      <p>Create career paths as private drafts, edit them, and publish them for all TigerPad users.</p>
      <Notice notice={notice} />
      <form className="auth-form" onSubmit={save}>
        <div className="form-row">
          <label>Career path name
            <input required maxLength={150} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Cloud Systems Administrator" />
          </label>
          <label>Unique career path code
            <input required maxLength={40} value={form.career_path_code} onChange={(e) => setForm({ ...form, career_path_code: e.target.value })} placeholder="e.g. CLOUD_SYS_ADMIN" />
          </label>
        </div>
        <div className="form-row">
          <label>Industry
            <select required style={selectStyle} value={form.industry_id} onChange={(e) => setForm({ ...form, industry_id: e.target.value })}>
              <option value="">Select industry</option>
              {industries.map((item) => <option key={item.industry_id} value={item.industry_id}>{item.name}</option>)}
            </select>
          </label>
          <label>Typical education level
            <input maxLength={50} value={form.typical_education_level} onChange={(e) => setForm({ ...form, typical_education_level: e.target.value })} placeholder="e.g. Bachelor's degree" />
          </label>
        </div>
        <label>Description
          <textarea style={textareaStyle} rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </label>
        <div className="form-row">
          <button type="submit" className="secondary-button" disabled={busy}>{busy ? "Saving..." : editingId ? "Save changes" : "Save as draft"}</button>
          {editingId && <button type="button" className="text-button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>Cancel editing</button>}
        </div>
      </form>
      <div style={{ marginTop: "22px" }}>
        <label>Show career paths
          <select style={selectStyle} value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All ({paths.length})</option>
            <option value="draft">Drafts ({paths.filter((p) => !p.is_active).length})</option>
            <option value="published">Published ({paths.filter((p) => p.is_active).length})</option>
          </select>
        </label>
        {shown.length === 0 && <p>No career paths in this category.</p>}
        {shown.map((path) => (
          <div key={path.career_path_id} style={{ borderTop: "1px solid #dce3ee", padding: "14px 0" }}>
            <strong>{path.name}</strong>
            <p>{path.career_path_code} · {industries.find((i) => i.industry_id === path.industry_id)?.name || "Industry #" + path.industry_id} · {path.is_active ? "Published" : "Draft"}</p>
            <p>{path.description || "No description"}</p>
            <div className="form-row">
              <button type="button" className="text-button" disabled={busy} onClick={() => startEdit(path)}>Edit</button>
              <button type="button" className="secondary-button" disabled={busy} onClick={() => setPublished(path)}>{path.is_active ? "Unpublish" : "Publish"}</button>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

// Audit history is deliberately separated from the administrator dashboard.
// The API supplies the available records; searching only filters the loaded set.
function AdminAuditLogsView({ healthStatus, onBack, onOpen, navigation = [] }) {
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditSearch, setAuditSearch] = useState("");
  const [selectedAudit, setSelectedAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState(null);

  async function loadAuditLogs() {
    setLoading(true);
    setNotice(null);
    try {
      const result = await apiRequest("/admin/audit-logs");
      setAuditLogs(asArray(result));
      setSelectedAudit(null);
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const visibleAuditLogs = auditLogs.filter((item) => {
    const query = auditSearch.trim().toLowerCase();
    if (!query) return true;
    return [
      item.action, item.entity_type, item.entity_id, item.description,
      item.event_category, item.status, item.severity_level, item.user_id,
    ].some((value) => String(value ?? "").toLowerCase().includes(query));
  });

  return (
    <>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">Administrator · Security history</p>
          <h1>Audit Logs</h1>
          <p className="dashboard-intro">Review recorded administrative and security activity in TigerPad.</p>
        </div>
        <HealthPill healthStatus={healthStatus} />
      </div>
      {onOpen && <QuickTabs navigation={navigation} onOpen={onOpen} />}
      <Notice notice={notice} />
      <article className="dashboard-card" style={{ marginTop: 24 }}>
        <p className="card-label">About audit logs</p>
        <h2>Understand system activity</h2>
        <p>Audit logs help administrators investigate recorded changes, check account-management actions, and review unusual events. Each record may include an action, description, severity, time, and affected entity.</p>
        <p>These logs are read-only. Use <strong>View record</strong> to inspect an event without changing it.</p>
      </article>
      <article className="dashboard-card" style={{ marginTop: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <div>
            <p className="card-label">Security history</p>
            <h2>Recorded events</h2>
            <p>{visibleAuditLogs.length} of {auditLogs.length} loaded records shown</p>
          </div>
          <button type="button" className="secondary-button" onClick={loadAuditLogs} disabled={loading}>
            {loading ? "Loading…" : "Refresh logs"}
          </button>
        </div>
        <label style={{ display: "block", marginTop: 18 }}>
          Filter loaded audit records
          <input
            value={auditSearch}
            onChange={(event) => setAuditSearch(event.target.value)}
            placeholder="Search action, description, status, severity, or user ID"
          />
        </label>
        <p style={{ marginTop: 8, opacity: 0.8 }}>
          Search is case-insensitive and updates as you type. It filters only the records currently loaded; use Refresh logs to request the latest records.
        </p>
        {loading && !auditLogs.length ? <p>Loading audit history…</p> : null}
        {!loading && !visibleAuditLogs.length ? <p>{auditSearch.trim() ? "No loaded records match this filter." : "No audit records available."}</p> : null}
        {visibleAuditLogs.map((item) => {
          const isSelected = selectedAudit?.audit_log_id === item.audit_log_id;
          return (
            <div key={item.audit_log_id} style={{ borderTop: "1px solid #315575", padding: "14px 0" }}>
              <strong>{displayLabel(item.action, "Recorded event")}</strong>
              <p>{item.description || "No description"} · {displayLabel(item.severity_level, "Severity not provided")} · {item.occurred_at ? new Date(item.occurred_at).toLocaleString() : "Time not provided"}</p>
              <button type="button" className="text-button" aria-expanded={isSelected} onClick={() => setSelectedAudit(isSelected ? null : item)}>
                {isSelected ? "Hide record" : "View record"}
              </button>
              {isSelected && (
                <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", overflowX: "auto", marginTop: 12, padding: 14, borderRadius: 10, background: "#071d31", color: "#fff", fontSize: 13, lineHeight: 1.6 }}>
                  {JSON.stringify(item, null, 2)}
                </pre>
              )}
            </div>
          );
        })}
      </article>
    </>
  );
}

// Dedicated administrator account management. Backend enforces admin-only access.
function AdminUserManagementView({ healthStatus, onOpen, navigation = [], currentUser }) {
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [busyUserId, setBusyUserId] = useState(null);
  const [notice, setNotice] = useState(null);

  async function loadUsers() {
    setLoading(true);
    setNotice(null);
    try {
      const response = await apiRequest("/admin/users");
      setUsers(asArray(response));
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadUsers(); }, []);

  async function updateRole(item, roleName) {
    if (roleName === item.role) return;
    if (!window.confirm(`Change ${item.first_name || "this user"}'s role to ${displayLabel(roleName)}?`)) return;
    const roleIds = { student: 1, faculty: 2, admin: 3 };
    setBusyUserId(item.user_id);
    setNotice(null);
    try {
      const saved = await apiRequest(`/admin/users/${item.user_id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role_id: roleIds[roleName] }),
      });
      setUsers((current) => current.map((user) => user.user_id === item.user_id ? { ...user, ...saved } : user));
      setNotice({ type: "success", text: "Account role updated." });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusyUserId(null);
    }
  }

  async function updateStatus(item) {
    const nextActive = !item.is_active;
    if (!window.confirm(`${nextActive ? "Activate" : "Deactivate"} the account for ${item.jsu_email}?`)) return;
    setBusyUserId(item.user_id);
    setNotice(null);
    try {
      const saved = await apiRequest(`/admin/users/${item.user_id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: nextActive }),
      });
      setUsers((current) => current.map((user) => user.user_id === item.user_id ? { ...user, ...saved } : user));
      setNotice({ type: "success", text: `Account ${nextActive ? "activated" : "deactivated"}.` });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusyUserId(null);
    }
  }

  const filteredUsers = users.filter((item) => {
    const role = String(item.role || "student").toLowerCase();
    const term = `${item.first_name || ""} ${item.last_name || ""} ${item.jsu_email || ""} ${item.user_id}`.toLowerCase();
    return (!search.trim() || term.includes(search.trim().toLowerCase()))
      && (roleFilter === "all" || role === roleFilter)
      && (statusFilter === "all" || (statusFilter === "active" ? !!item.is_active : !item.is_active));
  });

  return (
    <>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">Administrator · Account management</p>
          <h1>Manage Users</h1>
          <p className="dashboard-intro">Find TigerPad accounts, review their roles, and activate or deactivate access.</p>
        </div>
        <HealthPill healthStatus={healthStatus} />
      </div>
      {onOpen && <QuickTabs navigation={navigation} onOpen={onOpen} />}
      <Notice notice={notice} />
      <article className="dashboard-card" style={{ marginTop: 24 }}>
        <p className="card-label">Account administration</p>
        <h2>How to manage users</h2>
        <p>Search by name, JSU email, or user ID. Filter by role and account status. Changing a role updates the user's permissions; deactivating an account restricts access without deleting their information. Changes require confirmation and are saved through the administrator API.</p>
        <p>Use caution with administrator roles. Only authorized administrators should manage accounts.</p>
      </article>
      <article className="dashboard-card" style={{ marginTop: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <p className="card-label">User directory</p>
            <h2>Accounts</h2>
            <p>{filteredUsers.length} of {users.length} loaded accounts shown</p>
          </div>
          <button type="button" className="secondary-button" onClick={loadUsers} disabled={loading || busyUserId !== null}>{loading ? "Loading…" : "Refresh users"}</button>
        </div>
        <div className="form-row" style={{ marginTop: 18 }}>
          <label style={{ flex: 2 }}>Search users
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, JSU email, or user ID" />
          </label>
          <label>Role
            <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} style={selectStyle}>
              <option value="all">All roles</option><option value="student">Student</option><option value="faculty">Faculty</option><option value="admin">Administrator</option>
            </select>
          </label>
          <label>Status
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} style={selectStyle}>
              <option value="all">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option>
            </select>
          </label>
        </div>
        <p style={{ opacity: 0.8, marginTop: 8 }}>Filters apply to the accounts currently loaded. Refresh to retrieve the latest available accounts.</p>
        {loading && !users.length && <p>Loading accounts…</p>}
        {!loading && !filteredUsers.length && <p>{search || roleFilter !== "all" || statusFilter !== "all" ? "No accounts match your filters." : "No accounts available."}</p>}
        {filteredUsers.map((item) => {
          const isSelf = String(item.user_id) === String(currentUser?.user_id);
          const busy = busyUserId !== null;
          return (
            <div key={item.user_id} style={{ borderTop: "1px solid #315575", padding: "16px 0" }}>
              <strong>{item.first_name} {item.last_name} {isSelf ? "(Your account)" : ""}</strong>
              <p>{item.jsu_email} · User #{item.user_id}</p>
              <div className="form-row">
                <label>Role
                  <select value={String(item.role || "student").toLowerCase()} disabled={busy || isSelf} onChange={(event) => updateRole(item, event.target.value)} style={selectStyle}>
                    <option value="student">Student</option><option value="faculty">Faculty</option><option value="admin">Administrator</option>
                  </select>
                </label>
                <div>
                  <span className="card-label">Status</span>
                  <p>{item.is_active ? "Active" : "Inactive"}</p>
                  <button type="button" className="text-button" disabled={busy || isSelf} onClick={() => updateStatus(item)}>
                    {busyUserId === item.user_id ? "Saving…" : item.is_active ? "Deactivate" : "Activate"}
                  </button>
                </div>
              </div>
              {isSelf && <p style={{ opacity: 0.75 }}>You cannot change your own role or status from this page.</p>}
            </div>
          );
        })}
      </article>
    </>
  );
}

function AdminView({ healthStatus, onBack, onOpen, navigation = [], showPageHeader = true }) {
  const [overview, setOverview] = useState(null);
  const [programAccess, setProgramAccess] = useState([]);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    Promise.allSettled([apiRequest("/admin/overview"), apiRequest("/admin/faculty-access")]).then((results) => {
      if (results[0].status === "fulfilled") setOverview(results[0].value);
      else setNotice({ type: "error", text: results[0].reason?.message || "Could not load admin overview." });
      if (results[1].status === "fulfilled") setProgramAccess(asArray(results[1].value));
    });
  }, []);

  return (
    <>
      {showPageHeader && <PageHeader onBack={onBack} />}
      <div className="welcome-row">
        <div>
          <p className="eyebrow">Administrator workspace</p>
          <h1>Manage TigerPad.</h1>
          <p className="dashboard-intro">Review account totals and faculty permissions. Use Manage Users to update individual accounts.</p>
        </div>
        <HealthPill healthStatus={healthStatus} />
      </div>
      {onOpen && <QuickTabs navigation={navigation} onOpen={onOpen} />}
      <Notice notice={notice} />
      <div className="dashboard-grid" style={{ marginTop: 24 }}>
        {[["Users", overview?.total_users], ["Students", overview?.student_users], ["Faculty", overview?.faculty_users], ["Active career paths", overview?.total_active_career_paths]].map(([label, value]) => (
          <article className="dashboard-card score-card" key={label}><p className="card-label">{label}</p><strong>{value ?? "—"}</strong></article>
        ))}
      </div>
      <article className="dashboard-card" style={{ marginTop: 24 }}>
        <p className="card-label">Account management</p>
        <h2>Manage user accounts</h2>
        <p>Update student, faculty, and administrator account roles and activation status from a dedicated page.</p>
        <button type="button" className="secondary-button" onClick={() => onOpen("manage-users")}>Open Manage Users</button>
      </article>
      <article className="dashboard-card" style={{ marginTop: 24 }}>
        <p className="card-label">Faculty permissions</p>
        <h2>Program access records</h2>
        {programAccess.length ? (
          <ul>{programAccess.map((item) => (
            <li key={item.faculty_program_access_id}>Faculty profile #{item.faculty_profile_id} · Program #{item.program_id} · {displayLabel(item.access_level)} · {item.is_active ? "Active" : "Inactive"}</li>
          ))}</ul>
        ) : <p>No faculty program-access records are currently loaded.</p>}
      </article>
    </>
  );
}

// Root component.
export default function App() {
  const [user, setUser] = useState(null);
  const [healthStatus, setHealthStatus] = useState("checking");

  useEffect(() => {
    fetch(HEALTH_URL)
      .then((response) =>
        response.json().then((payload) => ({
          response,
          payload,
        })),
      )
      .then(({ response, payload }) =>
        setHealthStatus(
          response.ok && payload.status === "healthy"
            ? "online"
            : "degraded",
        ),
      )
      .catch(() => setHealthStatus("offline"));

    if (token() || COOKIE_AUTH_ENABLED) {
      apiRequest("/auth/me")
        .then(setUser)
        .catch(() => {
          sessionStorage.removeItem(
            "tigerpad_access_token",
          );
          sessionStorage.removeItem(
            "tigerpad_refresh_token",
          );
        });
    }
  }, []);

  async function logout() {
    try {
      if (refreshToken()) {
        await apiRequest("/auth/logout", {
          method: "POST",
          body: JSON.stringify({
            refresh_token: refreshToken(),
            all_sessions: false,
          }),
        });
      }
    } catch {
      // Local credentials are still removed when the server request fails.
    }

    if (user?.user_id != null) {
      sessionStorage.removeItem(`tigerpad_faculty_recent_students_${user.user_id}`);
    }
    sessionStorage.removeItem("tigerpad_access_token");
    sessionStorage.removeItem("tigerpad_refresh_token");
    setUser(null);
  }

  if (!user) {
    return (
      <AuthView
        healthStatus={healthStatus}
        onAuthenticated={setUser}
      />
    );
  }

  return (
    <AuthenticatedApp
      user={user}
      healthStatus={healthStatus}
      onLogout={logout}
    />
  );
}
