<?php
ini_set('display_errors', 0);                // Hide errors from browser
ini_set('log_errors', 1);                    // Enable error logging
ini_set('error_log', __DIR__ . '/../error_log.txt'); // Save to /admin/error_log.txt
error_reporting(E_ALL);                      // Log all errors

require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';
$page_title = "Applicant Details";

/* -----------------------------
    Fetch Application Info
----------------------------- */
$applicant = null;
if (isset($_GET['id']) && is_numeric($_GET['id'])) {
    $application_id = (int)$_GET['id'];

    $query = "
        SELECT 
            a.*, 
            u.name AS applicant_name, 
            u.email, 
            u.phone, 
            u.age, 
            u.gender,
            u.address, 
            u.address2, 
            u.city, 
            u.country, 
            u.highest_degree,
            u.institution,
            u.graduation_year,
            p.position_name
        FROM job_applications a
        LEFT JOIN users u ON u.id = a.user_id
        LEFT JOIN job_positions p ON p.id = a.position_id
        WHERE a.id = $application_id
        LIMIT 1
    ";
    $result = $conn->query($query);
    if ($result && $result->num_rows > 0) {
        $applicant = $result->fetch_assoc();
    }
}

/* -----------------------------
    Fetch Application Comments
----------------------------- */
$comments = [];
if (!empty($applicant['id'])) {
    $cid = (int)$applicant['id'];
    $cquery = "
        SELECT ac.*, u.name AS author_name
        FROM application_comments ac
        LEFT JOIN users u ON u.id = ac.user_id
        WHERE ac.application_id = $cid
        ORDER BY ac.created_at DESC
    ";
    $cres = $conn->query($cquery);
    if ($cres) {
        while ($r = $cres->fetch_assoc()) {
            $comments[] = $r;
        }
    }
}

include __DIR__ . '/../includes/header.php';
?>

<style>
.card { border-radius: 0.75rem; overflow: hidden; border: none; }
.card-header { font-weight: 600; font-size: 1rem; }
.highlight-header { background: linear-gradient(90deg, #198754, #146c43); color: #fff !important; }
.info-card { border-top: 4px solid #198754; }
.list-group-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.75rem 1rem; border-bottom: 1px solid #e9ecef;
}
.comment-box {
    background: #f8f9fa; border-radius: 0.5rem;
    padding: 1rem; border: 1px solid #dee2e6; margin-bottom: 1rem;
    position: relative;
}
.comment-actions {
    position: absolute; top: 10px; right: 10px;
}
.delete-section {
    border-top: 1px solid #eee; background: #fff8f8;
    padding: 1rem; text-align: right;
}
</style>

<div class="container py-4">
<?php if ($applicant): ?>
  
  <div class="d-flex justify-content-between align-items-center mb-4">
      <nav aria-label="breadcrumb">
          <ol class="breadcrumb mb-0">
              <li class="breadcrumb-item"><a href="/admin/dashboard.php">Back</a></li>
          </ol>
      </nav>
      <?php if(isset($_GET['msg'])): ?>
          <?php if($_GET['msg'] == 'updated'): ?> <span class="badge bg-success">Comment Updated</span> <?php endif; ?>
          <?php if($_GET['msg'] == 'deleted'): ?> <span class="badge bg-danger">Comment Deleted</span> <?php endif; ?>
      <?php endif; ?>
  </div>

  <h3 class="fw-bold mb-4 border-bottom pb-2 text-dark">
    Applicant: <?= htmlspecialchars($applicant['applicant_name'] ?? 'N/A') ?>
  </h3>

  <div class="row g-4">
    <div class="col-lg-5">
      <div class="card shadow-sm border-0">
        <div class="card-header highlight-header">Application Summary</div>
        <ul class="list-group list-group-flush">
          <li class="list-group-item"><span class="fw-bold text-muted">Position:</span><span class="fw-bold text-success"><?= htmlspecialchars($applicant['position_name'] ?? 'N/A') ?></span></li>
          <li class="list-group-item">
            <span class="fw-bold text-muted">Status:</span>
            <select id="statusDropdown" class="form-select form-select-sm w-auto fw-bold" data-id="<?= $applicant['id'] ?>">
              <?php
              $statuses = ['New', 'Screening', 'Interview', 'Offer', 'Hired','Future Consideration', 'Rejected'];
              foreach ($statuses as $status) {
                  $sel = ($status === $applicant['status']) ? 'selected' : '';
                  echo "<option value='$status' $sel>$status</option>";
              }
              ?>
            </select>
          </li>
          <li class="list-group-item"><span class="fw-medium">Applied Date:</span><span><?= date('M d, Y', strtotime($applicant['applied_at'])) ?></span></li>
          <li class="list-group-item"><span class="fw-medium">Experience:</span><span><?= htmlspecialchars($applicant['years_experience'] ?? '—') ?> Years</span></li>
          <li class="list-group-item"><span class="fw-medium">Expected Salary:</span><span>IQD <?= number_format((float)$applicant['expected_salary'], 0) ?></span></li>
          <li class="list-group-item">
            <span class="fw-medium">Resume:</span>
            <a href="../<?= htmlspecialchars($applicant['resume_path']) ?>" target="_blank" class="btn btn-sm btn-outline-success">
              <i class="bi bi-file-earmark-pdf"></i> View CV
            </a>
          </li>
        </ul>

        <div class="delete-section">
          <form method="post" action="/admin/delete_application.php" onsubmit="return confirm('WARNING: This will permanently delete the application. Continue?');">
            <input type="hidden" name="id" value="<?= $applicant['id'] ?>">
            <button type="submit" class="btn btn-sm btn-danger fw-bold">
              <i class="bi bi-trash"></i> Delete Application
            </button>
          </form>
        </div>
      </div>
    </div>

    <div class="col-lg-7">
      <div class="card shadow-sm info-card mb-4">
        <div class="card-header bg-white text-dark border-bottom fw-bold">Personal & Contact Details</div>
        <ul class="list-group list-group-flush">
          <li class="list-group-item"><span class="text-muted">Email:</span><strong><?= htmlspecialchars($applicant['email'] ?? 'N/A') ?></strong></li>
          <li class="list-group-item"><span class="text-muted">Phone:</span><strong><?= htmlspecialchars($applicant['phone'] ?? 'N/A') ?></strong></li>
          <li class="list-group-item"><span class="text-muted">Location:</span>
            <strong>
              <?php
                $parts = array_filter([$applicant['city'], $applicant['country']]);
                echo htmlspecialchars($parts ? implode(', ', $parts) : 'N/A');
              ?>
            </strong>
          </li>
          <li class="list-group-item"><span class="text-muted">Education:</span>
            <strong><?= htmlspecialchars($applicant['highest_degree'] ?? 'N/A') ?></strong>
          </li>
        </ul>
      </div>

      <div class="card shadow-sm">
        <div class="card-header bg-light border-bottom d-flex justify-content-between align-items-center">
          <span class="fw-bold"><i class="bi bi-chat-left-text me-2"></i> Comments</span>
          <span class="badge bg-success"><?= count($comments) ?></span>
        </div>
        <div class="card-body">
          <?php if (!empty($comments)): ?>
            <?php foreach ($comments as $c): ?>
              <?php
                // Determine comment "type"
                $applicantUserId = (int)($applicant['user_id'] ?? 0);
                $commentUserId   = (int)($c['user_id'] ?? 0);
                $isApplicantComment = ($commentUserId > 0 && $applicantUserId > 0 && $commentUserId === $applicantUserId);

                $isVisible = !empty($c['visible_to_applicant']); // 1 => visible
                // Color rules requested:
                // - Admin internal only => red
                // - Admin visible to applicant => green
                // - Applicant comments (visible to applicant) => orange
                $borderColor = 'secondary';
                if ($isApplicantComment && $isVisible) {
                    $borderColor = 'warning'; // orange
                } elseif (!$isApplicantComment && $isVisible) {
                    $borderColor = 'success'; // green
                } elseif (!$isApplicantComment && !$isVisible) {
                    $borderColor = 'danger';  // red
                } else {
                    // Applicant internal-only (rare) -> keep warning to distinguish applicant
                    $borderColor = $isApplicantComment ? 'warning' : 'secondary';
                }

                // Badge labeling (kept, but enhanced to reflect the 3 cases clearly)
                if ($isApplicantComment) {
                    $badgeColor = 'warning';
                    $badgeIcon  = 'bi-person-fill';
                    $badgeText  = 'Applicant Comment';
                } else {
                    if ($isVisible) {
                        $badgeColor = 'success';
                        $badgeIcon  = 'bi-eye-fill';
                        $badgeText  = 'Visible to Applicant';
                    } else {
                        $badgeColor = 'danger';
                        $badgeIcon  = 'bi-eye-slash-fill';
                        $badgeText  = 'Internal Only';
                    }
                }
              ?>

              <div class="comment-box shadow-sm border-start border-4 border-<?= $borderColor ?>">
                
                <div class="comment-actions">
                    <a href="edit_comment.php?id=<?= $c['id'] ?>" class="text-primary me-2" title="Edit"><i class="bi bi-pencil-square"></i></a>
                    <form action="delete_comment.php" method="POST" class="d-inline" onsubmit="return confirm('Delete this comment?');">
                        <input type="hidden" name="id" value="<?= $c['id'] ?>">
                        <input type="hidden" name="application_id" value="<?= $applicant['id'] ?>">
                        <button type="submit" class="border-0 bg-transparent text-danger p-0" title="Delete"><i class="bi bi-trash"></i></button>
                    </form>
                </div>

                <div class="mb-1">
                  <strong><?= htmlspecialchars($c['author_name'] ?? 'Administrator') ?></strong>
                  <small class="text-muted ms-2"><?= date('M d, H:i', strtotime($c['created_at'])) ?></small>
                </div>
                <p class="mb-2 text-dark" style="font-size: 0.95rem;"><?= nl2br(htmlspecialchars($c['comment'])) ?></p>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="badge rounded-pill bg-<?= $badgeColor ?> opacity-75" style="font-size: 0.7rem;">
                      <i class="bi <?= $badgeIcon ?>"></i>
                      <?= $badgeText ?>
                    </span>
                </div>
              </div>
            <?php endforeach; ?>
          <?php else: ?>
            <div class="text-center py-4">
                <i class="bi bi-chat-square-dots text-muted display-6"></i>
                <p class="text-muted mt-2 fst-italic">No internal or shared comments found.</p>
            </div>
          <?php endif; ?>

          <div class="mt-4 border-top pt-4">
              <h6 class="fw-bold mb-3">Add New Comment</h6>
              <form method="post" action="/admin/save_comment.php">
                <input type="hidden" name="application_id" value="<?= $applicant['id'] ?>">
                <div class="mb-3">
                  <textarea name="comment" class="form-control" rows="3" placeholder="Enter notes or feedback..." required></textarea>
                </div>
                <div class="row align-items-center">
                    <div class="col-md-6 mb-3 mb-md-0">
                        <select name="visible_to_applicant" class="form-select form-select-sm">
                            <option value="0">🔒 Admin Only (Internal)</option>
                            <option value="1">📢 Visible to Applicant (Send Email)</option>
                        </select>
                    </div>
                    <div class="col-md-6 text-md-end">
                        <button type="submit" class="btn btn-success btn-sm px-4 fw-bold shadow-sm">
                          <i class="bi bi-plus-lg"></i> Post Comment
                        </button>
                    </div>
                </div>
              </form>
          </div>
        </div>
      </div>
    </div>
  </div>

<?php else: ?>
  <div class="alert alert-danger text-center shadow-sm" role="alert">
    <h4 class="alert-heading">Application Not Found!</h4>
    <p>The record might have been removed or the ID is incorrect.</p>
    <hr>
    <a href="/admin/dashboard.php" class="btn btn-danger"><i class="bi bi-arrow-left"></i> Return to Dashboard</a>
  </div>
<?php endif; ?>
</div>

<script>
document.getElementById('statusDropdown')?.addEventListener('change', async (e) => {
    const id = e.target.dataset.id;
    const newStatus = e.target.value;
    e.target.disabled = true;

    try {
        const res = await fetch('/admin/update_status.php', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: `application_id=${id}&status=${encodeURIComponent(newStatus)}`
        });

        if (res.ok) {
            alert('✅ Status updated to ' + newStatus);
            location.reload(); // Reload to see if colors or emails triggered correctly
        } else {
            alert('❌ Failed to update status');
        }
    } catch (err) {
        alert('❌ Error connecting to server');
    } finally {
        e.target.disabled = false;
    }
});
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>
