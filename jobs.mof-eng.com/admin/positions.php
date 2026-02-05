<?php
// Configuration to display all errors (Good for development/debugging 500 errors)
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// Includes needed for both AJAX and HTML view.
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';
require __DIR__ . '/../includes/helpers.php'; // Assumed to contain e() for escaping HTML

/* ---------------------------------------------------------------
   1) AJAX HANDLERS - MUST EXECUTE AND EXIT IMMEDIATELY
---------------------------------------------------------------- */
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    header('Content-Type: application/json');

    $errorExit = function ($msg) {
        echo json_encode(['ok' => false, 'message' => $msg]);
        exit;
    };

    $successExit = function ($msg, $extra = []) {
        echo json_encode(array_merge(['ok' => true, 'message' => $msg], $extra));
        exit;
    };

    // ✅ Applicant status canonicalization + whitelist (fixes "Future Consideration" issues)
    $allowedApplicantStatuses = [
        'applied' => 'Applied',
        'screening' => 'Screening',
        'interview' => 'Interview',
        'offer' => 'Offer',
        'hired' => 'Hired',
        'rejected' => 'Rejected',
        'future consideration' => 'Future Consideration',
        'future_consideration' => 'Future Consideration',
        'futureconsideration' => 'Future Consideration',
    ];
    $normalizeApplicantStatus = function($s) use ($allowedApplicantStatuses) {
        $s = strtolower(trim((string)$s));
        $s = preg_replace('/\s+/', ' ', $s); // collapse spaces
        if (isset($allowedApplicantStatuses[$s])) return $allowedApplicantStatuses[$s];
        // also try converting underscores to spaces
        $s2 = str_replace('_', ' ', $s);
        $s2 = preg_replace('/\s+/', ' ', $s2);
        if (isset($allowedApplicantStatuses[$s2])) return $allowedApplicantStatuses[$s2];
        return null;
    };

    // ✅ Email sender helper (used for "new job position" notification)
    $sendNewJobEmailToAllUsers = function($positionId, $positionName, $location, $employmentType, $description) use ($conn) {
        $logo_url = "https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png";

        // IMPORTANT: Adjust this link if your job details/apply route is different
        $jobUrl = "https://jobs.mof-eng.com/apply.php?position_id=" . (int)$positionId;

        // Pull all users (basic filter: must have email)
        $res = $conn->query("SELECT name, email FROM users WHERE email IS NOT NULL AND email <> ''");
        if (!$res) return ['sent' => 0, 'failed' => 0, 'error' => $conn->error];

        $subject = "New Job Opening: " . $positionName;

        $headers = "MIME-Version: 1.0" . "\r\n";
        $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
        $headers .= "From: MOF HR Team <no-reply@mof-eng.com>" . "\r\n";

        $sent = 0;
        $failed = 0;

        while ($u = $res->fetch_assoc()) {
            $to = trim((string)($u['email'] ?? ''));
            if ($to === '') continue;

            $personName = $u['name'] ?? 'Candidate';

            $safePosition = htmlspecialchars((string)$positionName, ENT_QUOTES, 'UTF-8');
            $safeLoc = htmlspecialchars((string)$location, ENT_QUOTES, 'UTF-8');
            $safeType = htmlspecialchars((string)$employmentType, ENT_QUOTES, 'UTF-8');
            $safeDesc = nl2br(htmlspecialchars((string)$description, ENT_QUOTES, 'UTF-8'));

            $email_body = "
            <html>
            <body style='font-family: \"Segoe UI\", Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f9f9f9;'>
                <div style='max-width: 650px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>
                    
                    <div style='text-align: center; border-bottom: 2px solid #198754; padding-bottom: 20px; margin-bottom: 30px;'>
                        <img src='$logo_url' alt='MOF-ENG Logo' style='height: 50px; width: auto; margin-bottom: 10px;'>
                        <h2 style='color: #198754; margin: 0; font-size: 22px;'>New Job Opportunity</h2>
                    </div>

                    <p style='font-size: 16px;'>Dear <strong>" . htmlspecialchars((string)$personName, ENT_QUOTES, 'UTF-8') . "</strong>,</p>

                    <p>MOF-ENG has published a new job opening. You can review the details and apply online:</p>

                    <div style='background-color: #f8f9fa; border-left: 5px solid #198754; padding: 18px; margin: 22px 0; color: #444;'>
                        <div style='margin-bottom: 8px;'><strong>Position:</strong> $safePosition</div>
                        <div style='margin-bottom: 8px;'><strong>Location:</strong> " . ($safeLoc !== '' ? $safeLoc : '—') . "</div>
                        <div style='margin-bottom: 8px;'><strong>Type:</strong> " . ($safeType !== '' ? $safeType : '—') . "</div>
                        " . ($safeDesc !== '' ? "<div style='margin-top: 10px;'><strong>Description:</strong><br>$safeDesc</div>" : "") . "
                    </div>

                    <p style='margin-top: 26px; text-align: center;'>
                        <a href='$jobUrl'
                           style='background-color: #198754; color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>
                           View & Apply
                        </a>
                    </p>

                    <div style='margin-top: 50px; padding-top: 25px; border-top: 1px solid #eee;'>
                        <table style='width: 100%;'>
                            <tr>
                                <td style='vertical-align: top; width: 120px;'>
                                    <img src='$logo_url' alt='MOF-ENG' style='width: 100px; height: auto; margin-top: 10px;'>
                                </td>
                                <td style='vertical-align: top; padding-left: 20px; border-left: 1px solid #ddd;'>
                                    <p style='margin: 0; font-weight: bold; color: #198754;'>Best regards,</p>
                                    <p style='margin: 5px 0;'><strong>HR Recruitment Team</strong></p>

                                    <div style='font-size: 13px; color: #555; line-height: 1.6;'>
                                        <span style='color: #000; font-weight: bold;'>MANAGING OF FUTURE ENG COMPANY</span><br>
                                        <strong>Tel:</strong> 07705330101<br>
                                        <strong>Address:</strong> House NO. A1-345, New Chwarchra, Near Sara petrol station, Slemani, Iraq.<br>
                                        <strong>Web:</strong> <a href='https://www.mof-eng.com' style='color: #198754; text-decoration: none;'>www.mof-eng.com</a>
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </div>

                    <div style='margin-top: 40px; font-size: 11px; color: #999; text-align: center;'>
                        &copy; " . date('Y') . " MOF-ENG. All rights reserved.<br>
                        You received this email because you have an account on our job portal.
                    </div>
                </div>
            </body>
            </html>";

            $ok = mail($to, $subject, $email_body, $headers);
            if ($ok) $sent++; else $failed++;
        }

        return ['sent' => $sent, 'failed' => $failed, 'error' => null];
    };

    try {
        $act = $_POST['action'];

        if ($act === 'add') {
            $name = trim($_POST['position_name'] ?? '');
            $qty  = (int)($_POST['quantity'] ?? 1);

            $location = trim($_POST['location'] ?? '');
            $employment_type = strtolower(trim($_POST['employment_type'] ?? 'full time'));
            $description = trim($_POST['description'] ?? '');

            // ✅ NEW: enable/disable email notifications for new job posting
            $notify_email = isset($_POST['notify_email']) ? (int)$_POST['notify_email'] : 0;

            if ($name === '' || $qty < 1) $errorExit('Invalid position name or quantity.');
            if (!in_array($employment_type, ['full time','part time'], true)) {
                $errorExit('Invalid employment type. Allowed: full time / part time.');
            }

            $checkStmt = $conn->prepare("SELECT id FROM job_positions WHERE position_name = ?");
            $checkStmt->bind_param("s", $name);
            $checkStmt->execute();
            $result = $checkStmt->get_result();

            if ($result->num_rows > 0) $errorExit('Position already exists.');

            $stmt = $conn->prepare("
                INSERT INTO job_positions (position_name, quantity, status, location, employment_type, description)
                VALUES (?, ?, 'active', ?, ?, ?)
            ");
            if (!$stmt) $errorExit('Failed to prepare insert: ' . $conn->error);
            $stmt->bind_param("sisss", $name, $qty, $location, $employment_type, $description);

            $success = $stmt->execute();

            if (!$success) {
                $errorExit('Failed to add position.');
            }

            // ✅ get new position id for the email apply link
            $newId = (int)$conn->insert_id;

            // ✅ OPTIONAL: send email notification to all users
            $emailInfo = ['sent' => 0, 'failed' => 0, 'error' => null];
            if ($notify_email === 1) {
                $emailInfo = $sendNewJobEmailToAllUsers($newId, $name, $location, $employment_type, $description);
            }

            $msg = 'Position added successfully.';
            if ($notify_email === 1) {
                $msg .= " Email notification: sent {$emailInfo['sent']}, failed {$emailInfo['failed']}.";
                if (!empty($emailInfo['error'])) {
                    $msg .= " (Email error: " . $emailInfo['error'] . ")";
                }
            }

            $successExit($msg, [
                'position_id' => $newId,
                'email_sent' => $emailInfo['sent'] ?? 0,
                'email_failed' => $emailInfo['failed'] ?? 0
            ]);
        }

        if ($act === 'edit') {
            $id   = (int)($_POST['id'] ?? 0);
            $name = trim($_POST['position_name'] ?? '');
            $qty  = (int)($_POST['quantity'] ?? 1);

            $location = trim($_POST['location'] ?? '');
            $employment_type = strtolower(trim($_POST['employment_type'] ?? 'full time'));
            $description = trim($_POST['description'] ?? '');

            if ($id <= 0 || $name === '' || $qty < 1) $errorExit('Invalid input for edit.');
            if (!in_array($employment_type, ['full time','part time'], true)) {
                $errorExit('Invalid employment type. Allowed: full time / part time.');
            }

            $stmt = $conn->prepare("
                UPDATE job_positions
                SET position_name=?, quantity=?, location=?, employment_type=?, description=?
                WHERE id=?
            ");
            if (!$stmt) $errorExit('Failed to prepare update: ' . $conn->error);
            $stmt->bind_param("sisssi", $name, $qty, $location, $employment_type, $description, $id);
            $success = $stmt->execute();

            $success ? $successExit('Position updated.') : $errorExit('Failed to update position.');
        }

        if ($act === 'toggle') {
            $id  = (int)($_POST['id'] ?? 0);
            $new = ($_POST['new_status'] ?? 'inactive') === 'active' ? 'active' : 'inactive';

            if ($id <= 0) $errorExit('Invalid ID for toggle.');

            $stmt = $conn->prepare("UPDATE job_positions SET status=? WHERE id=?");
            if (!$stmt) $errorExit('Failed to prepare toggle: ' . $conn->error);
            $stmt->bind_param("si", $new, $id);
            $success = $stmt->execute();

            $success ? $successExit('Status changed to ' . ucfirst($new) . '.') : $errorExit('Failed to toggle status.');
        }

        if ($act === 'delete') {
            $id = (int)($_POST['id'] ?? 0);
            if ($id <= 0) $errorExit('Invalid ID for delete.');

            $stmt = $conn->prepare("DELETE FROM job_positions WHERE id=?");
            if (!$stmt) $errorExit('Failed to prepare delete: ' . $conn->error);
            $stmt->bind_param("i", $id);
            $success = $stmt->execute();

            $success ? $successExit('Position deleted.') : $errorExit('Failed to delete position.');
        }

        if ($act === 'fetch_applicants') {
            $posId = (int)($_POST['position_id'] ?? 0);
            $posName = trim($_POST['position_name'] ?? '');

            if ($posId <= 0 && $posName === '') $errorExit('Missing position identifier.');

            if ($posId > 0) {
                $stmt = $conn->prepare("
                    SELECT 
                        a.id AS application_id,
                        u.name AS applicant_name, u.email, u.phone,
                        a.status, a.applied_at
                    FROM job_applications a
                    LEFT JOIN users u ON u.id = a.user_id
                    WHERE a.position_id = ?
                    ORDER BY a.applied_at DESC
                ");
                if (!$stmt) $errorExit("Failed to prepare SQL: " . $conn->error);
                $stmt->bind_param("i", $posId);
            } else {
                $stmt = $conn->prepare("
                    SELECT 
                        a.id AS application_id,
                        u.name AS applicant_name, u.email, u.phone,
                        a.status, a.applied_at
                    FROM job_applications a
                    LEFT JOIN users u ON u.id = a.user_id
                    LEFT JOIN job_positions p ON p.id = a.position_id
                    WHERE LOWER(TRIM(p.position_name)) = LOWER(TRIM(?))
                    ORDER BY a.applied_at DESC
                ");
                if (!$stmt) $errorExit("Failed to prepare SQL: " . $conn->error);
                $stmt->bind_param("s", $posName);
            }

            if (!$stmt->execute()) $errorExit("Database query failed to execute: " . $stmt->error);

            $rows = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
            $successExit('Applicants loaded.', ['data' => $rows]);
        }

        // ✅ NEW: Update applicant status (this is where "Future Consideration" was failing)
        if ($act === 'update_applicant_status') {
            $appId = (int)($_POST['application_id'] ?? 0);
            $rawStatus = $_POST['status'] ?? '';

            if ($appId <= 0) $errorExit('Invalid application id.');

            $status = $normalizeApplicantStatus($rawStatus);
            if ($status === null) {
                $errorExit('Invalid status value.');
            }

            $stmt = $conn->prepare("UPDATE job_applications SET status=? WHERE id=?");
            if (!$stmt) $errorExit('Failed to prepare status update: ' . $conn->error);
            $stmt->bind_param("si", $status, $appId);

            if (!$stmt->execute()) {
                $errorExit('❌ Failed to update status: ' . $stmt->error);
            }

            // If nothing changed, treat as ok (avoid false “failed”)
            $successExit('✅ Status updated.', ['status' => $status]);
        }

        $errorExit('Unknown action');

    } catch (\Throwable $e) {
        $errorExit('A critical server exception occurred: ' . $e->getMessage());
    }
}

/* ---------------------------------------------------------------
   2) FETCH DATA & HTML VIEW GENERATION (ONLY runs if NOT AJAX)
---------------------------------------------------------------- */

$page_title = "Job Positions Management";
include __DIR__ . '/../includes/header.php';

// Main table data fetch
$rows = $conn->query("
    SELECT jp.id, jp.position_name, jp.quantity, jp.status,
           jp.location, jp.employment_type, jp.description,
           COUNT(ja.id) AS applicants
    FROM job_positions jp
    LEFT JOIN job_applications ja
      ON ja.position_id = jp.id
    GROUP BY jp.id
    ORDER BY jp.id DESC
");

// Stats for overview cards
$stats = [
  'positions' => (int)($conn->query("SELECT COUNT(*) c FROM job_positions")->fetch_assoc()['c'] ?? 0),
  'vacancies' => (int)($conn->query("SELECT COALESCE(SUM(quantity),0) q FROM job_positions WHERE status='active'")->fetch_assoc()['q'] ?? 0),
  'apps' => (int)($conn->query("SELECT COUNT(*) c FROM job_applications")->fetch_assoc()['c'] ?? 0),
  'active_pos_count' => (int)($conn->query("SELECT COUNT(*) AS c FROM job_positions WHERE status='active'")->fetch_assoc()['c'] ?? 0)
];
?>

<!-- --- HTML CONTENT --- -->
<style>
.overview-card { border:none;color:#fff;border-radius:14px;transition:transform .2s ease,box-shadow .2s ease; }
.overview-card:hover { transform:translateY(-4px);box-shadow:0 10px 20px rgba(0,0,0,.15); }
.overview-icon { font-size:2.5rem;opacity:.8; }
.bg-gradient-blue { background:linear-gradient(135deg,#007bff,#00a3ff); }
.bg-gradient-green { background:linear-gradient(135deg,#28a745,#20c997); }
.bg-gradient-purple { background:linear-gradient(135deg,#6f42c1,#9b59b6); }
.bg-gradient-orange { background:linear-gradient(135deg,#fd7e14,#f39c12); }
.card-label { font-size:.9rem;opacity:.9;letter-spacing:.5px; }
.card-value { font-size:2rem;font-weight:700; }
.btn .spinner-border { width:1rem;height:1rem;margin-right:.5rem; }
.filter-section { background-color:#f8f9fa;border-radius:8px;padding:1rem;margin-bottom:1rem; }
.filter-section .form-label { font-size:.875rem;font-weight:600;color:#495057;margin-bottom:.25rem; }
.filter-section .form-control,.filter-section .form-select { font-size:.875rem; }

/* small helper for applicants status select */
.status-select { min-width: 200px; }
</style>

<h3 class="fw-bold mb-4 text-dark">Job Positions Overview</h3>
<div class="row g-3 mb-4">
  <div class="col-md-4 col-lg-3">
    <div class="card overview-card bg-gradient-blue shadow-sm text-center">
      <div class="card-body">
        <i class="bi bi-briefcase overview-icon mb-2"></i>
        <div class="card-label">Total Positions</div>
        <div class="card-value"><?= $stats['positions'] ?></div>
      </div>
      <div class="card-footer bg-transparent border-0 text-white-50 small">All created job listings</div>
    </div>
  </div>
  <div class="col-md-4 col-lg-3">
    <div class="card overview-card bg-gradient-green shadow-sm text-center">
      <div class="card-body">
        <i class="bi bi-person-lines-fill overview-icon mb-2"></i>
        <div class="card-label">Total Vacancies</div>
        <div class="card-value"><?= $stats['vacancies'] ?></div>
      </div>
      <div class="card-footer bg-transparent border-0 text-white-50 small">Open slots in active positions</div>
    </div>
  </div>
  <div class="col-md-4 col-lg-3">
    <div class="card overview-card bg-gradient-purple shadow-sm text-center">
      <div class="card-body">
        <i class="bi bi-people-fill overview-icon mb-2"></i>
        <div class="card-label">Total Applicants</div>
        <div class="card-value"><?= $stats['apps'] ?></div>
      </div>
      <div class="card-footer bg-transparent border-0 text-white-50 small">Total applications received</div>
    </div>
  </div>
  <div class="col-md-4 col-lg-3">
    <div class="card overview-card bg-gradient-orange shadow-sm text-center">
      <div class="card-body">
        <i class="bi bi-bar-chart-line-fill overview-icon mb-2"></i>
        <div class="card-label">Active Positions</div>
        <div class="card-value"><?= $stats['active_pos_count'] ?></div>
      </div>
      <div class="card-footer bg-transparent border-0 text-white-50 small">Currently visible to candidates</div>
    </div>
  </div>
</div>

<div id="statusMessage" class="mb-4"></div>

<div class="card border-0 shadow-sm mb-4">
  <div class="card-header bg-light fw-semibold">Add New Job Position</div>
  <div class="card-body">
    <form id="addForm" class="row g-3">
      <div class="col-md-6">
        <label class="form-label">Position Name</label>
        <input name="position_name" class="form-control" placeholder="e.g. Safety Officer" required>
      </div>
      <div class="col-md-3">
        <label class="form-label">Vacancies</label>
        <input type="number" name="quantity" class="form-control" min="1" value="1" required>
      </div>
      <div class="col-md-3">
        <label class="form-label">Location</label>
        <input type="text" name="location" class="form-control" placeholder="e.g. Sulaymaniyah">
      </div>
      <div class="col-md-3">
        <label class="form-label">Employment Type</label>
        <select name="employment_type" class="form-select">
          <option value="full time" selected>Full time</option>
          <option value="part time">Part time</option>
        </select>
      </div>

      <!-- ✅ NEW: Email notification toggle -->
      <div class="col-md-9 d-flex align-items-end">
        <div class="form-check mt-2">
          <input class="form-check-input" type="checkbox" value="1" id="notifyEmail" name="notify_email">
          <label class="form-check-label fw-semibold" for="notifyEmail">
            Send Email Notification to All Users (New Job)
          </label>
          <div class="text-muted small">If enabled, all registered users will receive an email with a link to apply.</div>
        </div>
      </div>

      <div class="col-12">
        <label class="form-label">Description</label>
        <textarea name="description" class="form-control" rows="3" placeholder="Brief job description / requirements..."></textarea>
      </div>
      <div class="col-md-3 ms-auto">
        <button type="submit" class="btn btn-primary w-100" id="addBtn">
          <i class="bi bi-plus-circle"></i> Add Position
        </button>
      </div>
    </form>
  </div>
</div>

<div class="card border-0 shadow-sm mb-4">
  <div class="card-header bg-light fw-semibold">Manage Job Positions</div>
  <div class="card-body">
    <div class="filter-section">
      <div class="row g-3 align-items-end">
        <div class="col-md-3">
          <label class="form-label"><i class="bi bi-search me-1"></i>Search Position</label>
          <input type="text" id="filterPosition" class="form-control" placeholder="Type position name...">
        </div>
        <div class="col-md-2">
          <label class="form-label"><i class="bi bi-geo-alt me-1"></i>Location</label>
          <input type="text" id="filterLocation" class="form-control" placeholder="Location...">
        </div>
        <div class="col-md-2">
          <label class="form-label"><i class="bi bi-briefcase me-1"></i>Type</label>
          <select id="filterType" class="form-select">
            <option value="">All Types</option>
            <option value="full time">Full Time</option>
            <option value="part time">Part Time</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="form-label"><i class="bi bi-toggle-on me-1"></i>Status</label>
          <select id="filterStatus" class="form-select">
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
        <div class="col-md-3">
          <button type="button" id="clearFilters" class="btn btn-outline-secondary w-100">
            <i class="bi bi-x-circle me-1"></i>Clear Filters
          </button>
        </div>
      </div>
      <div class="row mt-2">
        <div class="col-12">
          <small class="text-muted">
            <i class="bi bi-info-circle me-1"></i>
            Showing <span id="filteredCount" class="fw-bold">0</span> of <span id="totalCount" class="fw-bold">0</span> positions
          </small>
        </div>
      </div>
    </div>

    <div class="table-responsive">
      <table class="table table-bordered align-middle text-center" id="posTable">
        <thead class="table-light">
          <tr>
            <th>#</th>
            <th>Position</th>
            <th>Vacancies</th>
            <th>Applicants</th>
            <th>Status</th>
            <th>Location</th>
            <th>Type</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <?php
          $i = 1;
          while ($r = $rows->fetch_assoc()):
            $location = $r['location'] ?? '';
            $employment_type = $r['employment_type'] ?? 'full time';
            $description = $r['description'] ?? '';
          ?>
          <tr
            data-id="<?= e($r['id']) ?>"
            data-position="<?= e($r['position_name']) ?>"
            data-posid="<?= e($r['id']) ?>"
            <?php if ($location): ?>data-location="<?= e($location) ?>"<?php endif; ?>
            <?php if ($employment_type): ?>data-type="<?= e($employment_type) ?>"<?php endif; ?>
            <?php if ($description): ?>data-description="<?= e($description) ?>"<?php endif; ?>
          >
            <td class="row-number"><?= $i++ ?></td>
            <td class="pos-name text-start"><?= e($r['position_name']) ?></td>
            <td class="pos-qty"><?= e($r['quantity']) ?></td>
            <td>
              <span class="badge applicants-badge <?= $r['applicants'] > 0 ? 'bg-primary' : 'text-muted bg-light' ?>">
                <?= $r['applicants'] ?>
              </span>
            </td>
            <td>
              <span class="badge bg-<?= ($r['status']==='active' ? 'success' : 'secondary') ?> status">
                <?= ucfirst($r['status']) ?>
              </span>
            </td>
            <td class="pos-loc text-start"><?= e($location) ?></td>
            <td class="pos-type"><?= e(ucwords($employment_type)) ?></td>
            <td>
              <button type="button" class="btn btn-sm btn-outline-info viewBtn" title="View Applicants" <?= $r['applicants'] == 0 ? 'disabled' : '' ?>>
                <i class="bi bi-eye"></i>
              </button>
              <button type="button" class="btn btn-sm btn-outline-primary editBtn" title="Edit Position">
                <i class="bi bi-pencil"></i>
              </button>
              <button type="button" class="btn btn-sm btn-outline-warning toggleBtn" title="Toggle Status (Active/Inactive)">
                <i class="bi bi-power"></i>
              </button>
              <button type="button" class="btn btn-sm btn-outline-danger delBtn" title="Delete Position">
                <i class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
          <?php endwhile; ?>
        </tbody>
      </table>
    </div>
  </div>
</div>

<div class="card border-0 shadow-sm mb-5">
  <div class="card-header bg-light fw-semibold">Applicants per Position</div>
  <div class="card-body">
    <canvas id="posChart" height="120"></canvas>
  </div>
</div>

<!-- EDIT MODAL -->
<div class="modal fade" id="editModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="editForm">
        <div class="modal-header">
          <h5 class="modal-title">Edit Position</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <input type="hidden" name="id" id="edit-id">
          <div class="mb-3">
            <label class="form-label">Position Name</label>
            <input type="text" name="position_name" id="edit-name" class="form-control" required>
          </div>
          <div class="mb-3">
            <label class="form-label">Vacancies</label>
            <input type="number" name="quantity" id="edit-qty" class="form-control" min="1" required>
          </div>
          <div class="mb-3">
            <label class="form-label">Location</label>
            <input type="text" name="location" id="edit-location" class="form-control" placeholder="e.g. Sulaymaniyah">
          </div>
          <div class="mb-3">
            <label class="form-label">Employment Type</label>
            <select name="employment_type" id="edit-type" class="form-select">
              <option value="full time">Full time</option>
              <option value="part time">Part time</option>
            </select>
          </div>
          <div class="mb-1">
            <label class="form-label">Description</label>
            <textarea name="description" id="edit-description" class="form-control" rows="3" placeholder="Brief job description / requirements..."></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button type="submit" class="btn btn-primary" id="editBtn">Save Changes</button>
        </div>
      </form>
    </div>
  </div>
</div>

<!-- VIEW APPLICANTS MODAL -->
<div class="modal fade" id="applicantsModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-xl modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header d-flex justify-content-between align-items-center">
        <h5 class="modal-title flex-grow-1">Applicants for: <span id="applicantPosTitle" class="fw-bold"></span></h5>
        <button id="downloadCsvBtn" class="btn btn-success btn-sm me-3" style="display:none;" title="Download Data as CSV">
          <i class="bi bi-file-earmark-arrow-down"></i> Download CSV
        </button>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body" id="applicantsBody">
        <p class="text-center text-muted"><i class="bi bi-arrow-clockwise spinner-border spinner-border-sm me-2"></i> Loading Applicants...</p>
      </div>
    </div>
  </div>
</div>

<!-- GENERIC CONFIRMATION MODAL -->
<div class="modal fade" id="confirmationModal" tabindex="-1" aria-labelledby="confirmationModalLabel" aria-hidden="true">
  <div class="modal-dialog modal-sm">
    <div class="modal-content">
      <div class="modal-header bg-danger text-white">
        <h5 class="modal-title" id="confirmationModalLabel">Confirmation</h5>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body" id="confirmationModalBody"></div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-danger" id="confirmActionBtn">Confirm</button>
      </div>
    </div>
  </div>
</div>

<?php include __DIR__ . '/../includes/footer.php'; ?>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
window.currentApplicantsData = [];
window.currentPositionName = '';

/* ---------------------------------------------------------------
   UX AND UTILITY HELPERS
---------------------------------------------------------------- */
function showMessage(type, message, duration = 3000) {
    const container = document.getElementById('statusMessage');
    const alertHtml = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>`;
    container.innerHTML = alertHtml;
    setTimeout(() => {
        const alert = container.querySelector('.alert');
        if (alert) {
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                new bootstrap.Alert(alert).close();
            } else {
                alert.remove();
            }
        }
    }, duration);
}

function toggleLoading(btn, isLoading, defaultText) {
    if (!btn) return;
    const spinner = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;
    btn.disabled = isLoading;
    if (isLoading) {
        btn.setAttribute('data-original-html', btn.innerHTML);
        btn.innerHTML = spinner + ' Processing...';
    } else {
        btn.innerHTML = btn.getAttribute('data-original-html') || defaultText || btn.innerHTML;
        btn.removeAttribute('data-original-html');
    }
}

function drawChart(){
    const ctx = document.getElementById('posChart');
    if (!ctx) return;

    const visibleRows = [...document.querySelectorAll('#posTable tbody tr')].filter(tr => tr.style.display !== 'none');
    const labels = visibleRows.map(tr => tr.querySelector('.pos-name').innerText.trim());
    const data = visibleRows.map(tr => {
        const b = tr.querySelector('.applicants-badge');
        return b ? parseInt(b.innerText, 10) : 0;
    });

    if (window.posChartObj) window.posChartObj.destroy();
    window.posChartObj = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Applicants', data, backgroundColor: '#0d6efd' }] },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });
}

function showConfirmation(title, body, confirmCallback) {
    const modalEl = document.getElementById('confirmationModal');
    const titleEl = document.getElementById('confirmationModalLabel');
    const bodyEl = document.getElementById('confirmationModalBody');
    const confirmBtn = document.getElementById('confirmActionBtn');

    titleEl.textContent = title;
    bodyEl.innerHTML = body;

    confirmBtn.replaceWith(confirmBtn.cloneNode(true));
    const newConfirmBtn = document.getElementById('confirmActionBtn');

    newConfirmBtn.addEventListener('click', () => {
        confirmCallback();
        bootstrap.Modal.getInstance(modalEl).hide();
    }, { once: true });

    new bootstrap.Modal(modalEl).show();
}

function downloadCSV() {
    const data = window.currentApplicantsData;
    const position = window.currentPositionName || 'Applicants';

    if (data.length === 0) {
        showMessage('warning', 'No data to download.');
        return;
    }

    const headers = ["Name", "Email", "Phone", "Status", "Applied At"];
    const keys = ["applicant_name", "email", "phone", "status", "applied_at"];

    let csvContent = headers.join(",") + "\n";
    data.forEach(row => {
        const rowArray = keys.map(key => {
            let cell = row[key] === null || row[key] === undefined ? "" : String(row[key]);
            if (cell.includes(',') || cell.includes('"') || cell.includes('\n')) {
                cell = '"' + cell.replace(/"/g, '""') + '"';
            }
            return cell;
        });
        csvContent += rowArray.join(",") + "\n";
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);

    link.setAttribute("href", url);
    const filename = `${position.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_')}_Applicants.csv`;
    link.setAttribute("download", filename);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    showMessage('info', `Downloaded applicants for ${position}.`);
}

/* ---------------------------------------------------------------
   TABLE FILTERING
---------------------------------------------------------------- */
function applyFilters() {
    const positionFilter = document.getElementById('filterPosition').value.toLowerCase().trim();
    const locationFilter = document.getElementById('filterLocation').value.toLowerCase().trim();
    const typeFilter = document.getElementById('filterType').value.toLowerCase().trim();
    const statusFilter = document.getElementById('filterStatus').value.toLowerCase().trim();

    const rows = document.querySelectorAll('#posTable tbody tr');
    let visibleCount = 0;
    const totalCount = rows.length;

    rows.forEach((row) => {
        const position = row.querySelector('.pos-name')?.innerText.toLowerCase() || '';
        const location = row.querySelector('.pos-loc')?.innerText.toLowerCase() || '';
        const type = row.dataset.type?.toLowerCase() || '';
        const status = row.querySelector('.status')?.innerText.toLowerCase() || '';

        const matchesPosition = !positionFilter || position.includes(positionFilter);
        const matchesLocation = !locationFilter || location.includes(locationFilter);
        const matchesType = !typeFilter || type === typeFilter;
        const matchesStatus = !statusFilter || status === statusFilter;

        const isVisible = matchesPosition && matchesLocation && matchesType && matchesStatus;

        if (isVisible) {
            row.style.display = '';
            visibleCount++;
            row.querySelector('.row-number').textContent = visibleCount;
        } else {
            row.style.display = 'none';
        }
    });

    document.getElementById('filteredCount').textContent = visibleCount;
    document.getElementById('totalCount').textContent = totalCount;

    drawChart();
}

function clearFilters() {
    document.getElementById('filterPosition').value = '';
    document.getElementById('filterLocation').value = '';
    document.getElementById('filterType').value = '';
    document.getElementById('filterStatus').value = '';
    applyFilters();
}

/* ---------------------------------------------------------------
   AJAX POST WRAPPER
---------------------------------------------------------------- */
async function sendAction(fd, buttonElement, defaultText, successMessage) {
    if (buttonElement && buttonElement.id !== 'editBtn') {
        toggleLoading(buttonElement, true, defaultText);
    }

    try {
        const res = await fetch('', { method: 'POST', body: fd });
        const text = await res.text();
        let j;
        try {
            j = JSON.parse(text);
        } catch (e) {
            console.error('JSON Parse Error. Full response text:', text, e);
            showMessage('danger', 'CRITICAL ERROR: Server did not return valid JSON.');
            if (buttonElement) toggleLoading(buttonElement, false, defaultText);
            return;
        }

        if (j.ok) {
            showMessage('success', j.message || successMessage || 'Done.');
            setTimeout(() => window.location.reload(), 800);
        } else {
            showMessage('danger', j.message || 'Operation failed due to a server error.');
            if (buttonElement) toggleLoading(buttonElement, false, defaultText);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        showMessage('danger', 'Network error. Could not connect to server.');
        if (buttonElement) toggleLoading(buttonElement, false, defaultText);
    }
}

/* ---------------------------------------------------------------
   APPLICANT STATUS UPDATE (FIX)
---------------------------------------------------------------- */
function normalizeStatusClient(s) {
    if (!s) return '';
    let x = String(s).trim().toLowerCase().replace(/\s+/g, ' ');
    // allow variants
    if (x === 'future_consideration') x = 'future consideration';
    if (x === 'futureconsideration') x = 'future consideration';
    return x;
}

function badgeClassForStatus(status) {
    const s = normalizeStatusClient(status);
    if (s === 'hired') return 'success';
    if (s === 'rejected') return 'danger';
    if (s === 'screening') return 'warning';
    if (s === 'interview') return 'info';
    if (s === 'offer') return 'primary';
    if (s === 'future consideration') return 'dark';
    return 'secondary';
}

async function updateApplicantStatus(applicationId, newStatus, badgeEl) {
    const fd = new FormData();
    fd.append('action', 'update_applicant_status');
    fd.append('application_id', applicationId);
    fd.append('status', newStatus);

    try {
        const res = await fetch('', { method: 'POST', body: fd });
        const text = await res.text();
        let j;
        try { j = JSON.parse(text); } catch (e) {
            console.error('Malformed JSON from update_applicant_status:', text);
            showMessage('danger', '❌ Failed to update status (server response not JSON).');
            return false;
        }

        if (!j.ok) {
            showMessage('danger', j.message || '❌ Failed to update status.');
            return false;
        }

        const finalStatus = j.status || newStatus;

        if (badgeEl) {
            const cls = badgeClassForStatus(finalStatus);
            badgeEl.className = `badge bg-${cls}`;
            badgeEl.textContent = finalStatus;
        }

        // also update the in-memory CSV data
        const idx = window.currentApplicantsData.findIndex(x => String(x.application_id) === String(applicationId));
        if (idx >= 0) window.currentApplicantsData[idx].status = finalStatus;

        showMessage('success', j.message || '✅ Status updated.');
        return true;
    } catch (err) {
        console.error('Network error in updateApplicantStatus:', err);
        showMessage('danger', 'Network error. Could not update status.');
        return false;
    }
}

/* ---------------------------------------------------------------
   EVENT DELEGATION: Submits and Clicks
---------------------------------------------------------------- */
document.addEventListener('submit', async (e) => {
    if (e.target.id === 'addForm') {
        e.preventDefault();
        const btn = document.getElementById('addBtn');
        const defaultText = '<i class="bi bi-plus-circle"></i> Add Position';
        const fd = new FormData(e.target);
        fd.append('action', 'add');
        await sendAction(fd, btn, defaultText, 'Position added successfully. Reloading...');
    }

    if (e.target.id === 'editForm') {
        e.preventDefault();
        const btn = document.getElementById('editBtn');
        const defaultText = 'Save Changes';
        const fd = new FormData(e.target);
        fd.append('action', 'edit');

        const m = bootstrap.Modal.getInstance(document.getElementById('editModal'));
        if (m) m.hide();

        await sendAction(fd, btn, defaultText, 'Position updated successfully. Reloading...');
    }
});

document.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;

    const tr = btn.closest('tr');
    if (!tr) return;

    if (btn.classList.contains('viewBtn')) {
        const position = tr.dataset.position;
        const posId    = tr.dataset.posid;
        const body = document.getElementById('applicantsBody');
        const title = document.getElementById('applicantPosTitle');
        const downloadBtn = document.getElementById('downloadCsvBtn');

        title.textContent = position;
        body.innerHTML = '<p class="text-center text-muted"><i class="bi bi-arrow-clockwise spinner-border spinner-border-sm me-2"></i> Loading Applicants...</p>';
        downloadBtn.style.display = 'none';

        new bootstrap.Modal(document.getElementById('applicantsModal')).show();

        window.currentApplicantsData = [];
        window.currentPositionName = position;

        const fd = new FormData();
        fd.append('action', 'fetch_applicants');
        fd.append('position_id', posId);

        try {
            const res = await fetch('', { method: 'POST', body: fd });
            const text = await res.text();
            let j;

            try { j = JSON.parse(text); }
            catch (e) {
                console.error('Failed to parse JSON during applicant fetch. Full response:', text, e);
                body.innerHTML = '<p class="text-center text-danger">Failed to load applicants: Server returned malformed data.</p>';
                return;
            }

            if (j.ok && j.data.length) {
                window.currentApplicantsData = j.data;
                downloadBtn.style.display = 'inline-block';

                // ✅ Status options (includes Future Consideration)
                const statusOptions = [
                    'Applied','Screening','Interview','Offer','Hired','Rejected','Future Consideration'
                ];

                let html = `<div class="table-responsive"><table class="table table-sm table-bordered align-middle">
                    <thead class="table-light">
                      <tr>
                        <th>Name</th><th>Email</th><th>Phone</th>
                        <th>Status</th><th>Change Status</th><th>Applied At</th>
                      </tr>
                    </thead><tbody>`;

                j.data.forEach(a => {
                    const badge = badgeClassForStatus(a.status);
                    const appId = a.application_id;

                    const currentNorm = normalizeStatusClient(a.status);
                    const opts = statusOptions.map(opt => {
                        const optNorm = normalizeStatusClient(opt);
                        const sel = (optNorm === currentNorm) ? 'selected' : '';
                        return `<option value="${opt}" ${sel}>${opt}</option>`;
                    }).join('');

                    html += `<tr data-appid="${appId}">
                      <td>${a.applicant_name ?? ''}</td>
                      <td>${a.email ?? ''}</td>
                      <td>${a.phone ?? ''}</td>
                      <td><span class="badge bg-${badge} applicant-status-badge">${a.status ?? ''}</span></td>
                      <td>
                        <select class="form-select form-select-sm status-select">
                          ${opts}
                        </select>
                      </td>
                      <td>${a.applied_at ?? ''}</td>
                    </tr>`;
                });

                html += '</tbody></table></div>';
                body.innerHTML = html;

                // ✅ attach change listeners (inline update)
                body.querySelectorAll('tr[data-appid]').forEach(row => {
                    const select = row.querySelector('.status-select');
                    const badgeEl = row.querySelector('.applicant-status-badge');
                    const appId = row.getAttribute('data-appid');

                    if (!select) return;
                    select.addEventListener('change', async () => {
                        const newVal = select.value;
                        // optimistic UI: show as secondary while saving
                        if (badgeEl) {
                            badgeEl.className = 'badge bg-secondary applicant-status-badge';
                            badgeEl.textContent = 'Saving...';
                        }
                        const ok = await updateApplicantStatus(appId, newVal, badgeEl);
                        if (!ok) {
                            // if failed, revert badge to selected value visually (optional)
                            // re-fetching would be heavier; keep the select value as-is and show error
                        }
                    });
                });

            } else if (j.ok && !j.data.length) {
                window.currentApplicantsData = [];
                downloadBtn.style.display = 'none';
                body.innerHTML = '<p class="text-center text-muted">No applicants for this position.</p>';
            } else {
                window.currentApplicantsData = [];
                downloadBtn.style.display = 'none';
                body.innerHTML = `<p class="text-center text-danger">Server Error: ${j.message || 'Unknown error during fetch.'}</p>`;
            }
        } catch (error) {
            console.error('Fetch error in viewBtn:', error);
            window.currentApplicantsData = [];
            downloadBtn.style.display = 'none';
            body.innerHTML = '<p class="text-center text-danger">Network error: Could not connect to the server.</p>';
        }
    }

    if (btn.classList.contains('editBtn')) {
        document.getElementById('edit-id').value    = tr.dataset.id;
        document.getElementById('edit-name').value  = tr.querySelector('.pos-name').innerText.trim();
        document.getElementById('edit-qty').value   = tr.querySelector('.pos-qty').innerText.trim();

        document.getElementById('edit-location').value = tr.dataset.location || '';
        document.getElementById('edit-type').value     = (tr.dataset.type || 'full time').toLowerCase();
        document.getElementById('edit-description').value = tr.dataset.description || '';

        new bootstrap.Modal(document.getElementById('editModal')).show();
    }

    if (btn.classList.contains('toggleBtn')) {
        const id = tr.dataset.id;
        const currentStatusEl = tr.querySelector('.status');
        const current = currentStatusEl.innerText.trim().toLowerCase();
        const newStatus = current === 'active' ? 'inactive' : 'active';

        const defaultText = '<i class="bi bi-power"></i>';

        showConfirmation(
            'Confirm Status Change',
            `Are you sure you want to change the status of position ID ${id} from <strong>${ucfirst(current)}</strong> to <strong>${ucfirst(newStatus)}</strong>?`,
            async () => {
                const fd = new FormData();
                fd.append('action', 'toggle');
                fd.append('id', id);
                fd.append('new_status', newStatus);
                await sendAction(fd, btn, defaultText, 'Status successfully toggled. Reloading...');
            }
        );
    }

    if (btn.classList.contains('delBtn')) {
        const id = tr.dataset.id;
        const name = tr.dataset.position;

        const defaultText = '<i class="bi bi-trash"></i>';

        showConfirmation(
            'Confirm Position Deletion',
            `WARNING: You are about to permanently delete the position <strong>${name}</strong> (ID: ${id}). This action cannot be undone. Continue?`,
            async () => {
                const fd = new FormData();
                fd.append('action', 'delete');
                fd.append('id', id);
                await sendAction(fd, btn, defaultText, 'Position successfully deleted. Reloading...');
            }
        );
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const downloadCsvBtn = document.getElementById('downloadCsvBtn');
    if (downloadCsvBtn) downloadCsvBtn.addEventListener('click', downloadCSV);

    document.getElementById('filterPosition').addEventListener('input', applyFilters);
    document.getElementById('filterLocation').addEventListener('input', applyFilters);
    document.getElementById('filterType').addEventListener('change', applyFilters);
    document.getElementById('filterStatus').addEventListener('change', applyFilters);
    document.getElementById('clearFilters').addEventListener('click', clearFilters);

    applyFilters();
});

function ucfirst(str) {
    if (typeof str !== 'string' || str.length === 0) return str;
    return str.charAt(0).toUpperCase() + str.slice(1);
}

drawChart();
</script>
