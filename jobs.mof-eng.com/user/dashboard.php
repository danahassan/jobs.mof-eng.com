<?php
// /user/dashboard.php
require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';
require __DIR__ . '/../includes/helpers.php';

$page_title = "My Dashboard";
include __DIR__ . '/../includes/header.php';

$uid = (int)($_SESSION['user_id'] ?? 0);

// 1) Fetch user info
$stmt = $conn->prepare("SELECT * FROM users WHERE id=? LIMIT 1");
$stmt->bind_param("i", $uid);
$stmt->execute();
$user = $stmt->get_result()->fetch_assoc();
$stmt->close();

if (!$user) {
  echo '<div class="alert alert-danger mt-4 shadow-sm">User not found or session expired. Please <a href="/auth/login.php">login again</a>.</div>';
  include __DIR__ . '/../includes/footer.php';
  exit;
}

// 2) Fetch user job applications (join positions)
$appStmt = $conn->prepare("
  SELECT a.*, p.position_name
  FROM job_applications a
  JOIN job_positions p ON p.id = a.position_id
  WHERE a.user_id=?
  ORDER BY a.applied_at DESC
");
$appStmt->bind_param("i", $uid);
$appStmt->execute();
$apps = $appStmt->get_result();
$appStmt->close();

/* 🟢 Profile Picture Upload Logic */
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['profile_photo'])) {
  $uploadDir = __DIR__ . '/../uploads/profiles/';
  if (!is_dir($uploadDir)) mkdir($uploadDir, 0775, true);
  $file = $_FILES['profile_photo'];
  if ($file['error'] === UPLOAD_ERR_OK) {
    $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    if (in_array($ext, ['jpg','jpeg','png','gif'])) {
      $newName = 'user_' . $uid . '_' . time() . '.' . $ext;
      $dest = $uploadDir . $newName;
      if (move_uploaded_file($file['tmp_name'], $dest)) {
        $webPath = '/uploads/profiles/' . $newName;
        $up = $conn->prepare("UPDATE users SET profile_photo_path=? WHERE id=?");
        $up->bind_param("si", $webPath, $uid);
        $up->execute();
        $up->close();
        $user['profile_photo_path'] = $webPath;
        echo "<div class='alert alert-success mt-3'>✅ Profile picture updated successfully.</div>";
      } else echo "<div class='alert alert-danger mt-3'>❌ Failed to move uploaded file.</div>";
    } else echo "<div class='alert alert-warning mt-3'>⚠️ Only JPG, PNG, or GIF allowed.</div>";
  } else echo "<div class='alert alert-danger mt-3'>❌ Upload error. Try again.</div>";
}

/* 🟢 Default profile image logic */
$profile_photo = $user['profile_photo_path'] ?? '';
if (empty($profile_photo)) {
  if (($user['gender'] ?? '') === 'female')
    $profile_photo = '/uploads/profiles/default_female.png';
  else
    $profile_photo = '/uploads/profiles/default_male.png';
}
?>
<style>
.container-xl, .container-lg, .container-md, .container-sm{ max-width:1200px; }
.dashboard-header { font-weight: 800; color: #198754; margin-bottom: 1.8rem; }
.profile-card { border: none; border-radius: 14px; box-shadow: 0 6px 18px rgba(0,0,0,0.08); overflow: hidden; }
.profile-header { background: linear-gradient(90deg, #198754, #28a745); color: white; text-align: center; padding: 2rem 1rem; position: relative; }
.profile-header img { width: 120px; height: 120px; border-radius: 50%; border: 4px solid #fff; object-fit: cover; margin-bottom: .8rem; }
.profile-body { padding: 1.5rem; background: #ffffff; }
.profile-section { margin-bottom: 1.2rem; }
.profile-section h6 { font-weight: 700; color: #198754; border-bottom: 2px solid #d1f2e4; display: inline-block; padding-bottom: .3rem; margin-bottom: .6rem; }
.profile-info p { margin: 0.3rem 0; font-size: 0.95rem; }
.skill-badge { background-color: #e9f7ef; color: #198754; border-radius: 20px; padding: 0.3rem 0.75rem; font-size: 0.85rem; font-weight: 600; margin: 0.2rem; display: inline-block; }

.application-item { border: 1px solid #e9ecef; border-radius: .7rem; padding: 1.3rem; background: #fff; margin-bottom: 1.2rem; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
.app-title { color: #0d6efd; font-weight: 600; margin-bottom: 0.25rem; }
.app-details { color: #666; font-size: .9rem; }
.info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr)); gap: .5rem; }
.info-grid div { background: #f8f9fa; border-radius: .4rem; padding: .4rem .6rem; font-size: .9rem; }
.comment-box { background: #f9f9f9; padding: .8rem 1rem; border-radius: .5rem; margin-top: .6rem; }
.comment-box.admin { border-left: 4px solid #0d6efd; }
.comment-box.user { border-left: 4px solid #198754; }
.comment-author { font-weight: 600; font-size: .9rem; }
.comment-date { font-size: .8rem; color: #777; }
.comment-form textarea { resize: vertical; min-height: 70px; }
.edit-buttons { margin-top: .4rem; display: flex; gap: .5rem; }

/* 🟢 Add for edit button */
.edit-photo-btn {
  position: absolute;
  top: 1.2rem;
  right: 1.4rem;
  background: rgba(255,255,255,0.15);
  border: none;
  color: #fff;
  border-radius: 50%;
  padding: .4rem .5rem;
  cursor: pointer;
}
.edit-photo-btn:hover { background: rgba(255,255,255,0.3); }
.hidden-upload-form { display: none; margin-top: .5rem; }
</style>

<h3 class="dashboard-header">Welcome, <?= strtoupper(e($user['name'])) ?></h3>

<div class="row g-4">
  <div class="col-lg-4">
    <div class="card profile-card">
      <div class="profile-header">
        <img src="<?= e($profile_photo) ?>" alt="Profile Photo">
        <button class="edit-photo-btn" onclick="toggleUploadForm()"><i class="bi bi-pencil-square"></i></button>
        <h4 class="mb-0"><?= e($user['name']) ?></h4>
        <p class="mb-0" style="opacity:.9"><?= e($user['email']) ?></p>

        <!-- Hidden upload form -->
        <form id="uploadForm" class="hidden-upload-form" method="post" enctype="multipart/form-data">
          <input type="file" name="profile_photo" accept="image/*" class="form-control form-control-sm mb-2" required>
          <button class="btn btn-sm btn-light text-success fw-semibold"><i class="bi bi-upload"></i> Upload New</button>
        </form>
      </div>
      <div class="profile-body">
        <div class="profile-section profile-info">
          <h6><i class="bi bi-person-lines-fill"></i> Personal Info</h6>
          <p><i class="bi bi-telephone"></i>
            <?php
              $phone_number = e($user['phone'] ?? '—');
              if (!empty($user['areacode'])) $phone_number = "(" . e($user['areacode']) . ") " . $phone_number;
              echo $phone_number;
            ?>
          </p>
          <p><i class="bi bi-geo-alt"></i>
            <?php
              $parts = [];
              if (!empty($user['address']))  $parts[] = e($user['address']);
              if (!empty($user['address2'])) $parts[] = e($user['address2']);
              if (!empty($user['city']))     $parts[] = e($user['city']);
              if (!empty($user['country']))  $parts[] = e($user['country']);
              echo $parts ? implode(', ', $parts) : '—';
            ?>
          </p>
          <p><i class="bi bi-gender-ambiguous"></i> Gender: <?= e(ucfirst($user['gender'] ?? '—')) ?></p>
          <p><i class="bi bi-calendar"></i> Age: <?= e($user['age'] ?? '—') ?></p>
        </div>

        <div class="profile-section">
          <h6><i class="bi bi-mortarboard"></i> Education</h6>
          <p class="mb-1"><strong>Degree:</strong> <?= e($user['highest_degree'] ?? '—') ?></p>
          <p class="mb-1"><strong>Institution:</strong> <?= e($user['institution'] ?? '—') ?></p>
          <p class="mb-0"><strong>Graduation Year:</strong> <?= e($user['graduation_year'] ?? '—') ?></p>
        </div>

        <div class="profile-section">
          <h6><i class="bi bi-briefcase"></i> Experience</h6>
          <p class="mb-1"><strong>Title:</strong> <?= e($user['experience_title'] ?? '—') ?></p>
          <p class="mb-1"><strong>Company:</strong> <?= e($user['experience_company'] ?? '—') ?></p>
          <p class="mb-1"><strong>Years:</strong> <?= e($user['experience_years'] ?? '—') ?></p>
          <p class="mb-0 text-muted"><?= nl2br(e($user['experience_description'] ?? '')) ?></p>
        </div>

        <div class="profile-section">
          <h6><i class="bi bi-stars"></i> Skills</h6>
          <div>
            <?php
              $skills = array_filter(array_map('trim', explode(',', (string)($user['skills'] ?? ''))));
              if ($skills) {
                foreach ($skills as $s) echo '<span class="skill-badge">'. e($s) .'</span> ';
              } else {
                echo '<p class="text-muted small mb-0">No skills listed.</p>';
              }
            ?>
          </div>
        </div>

        <div class="text-center">
          <a href="/user/profile_edit.php" class="btn btn-sm btn-outline-primary"><i class="bi bi-pencil-square"></i> Edit Profile</a>
        </div>
      </div>
    </div>
  </div>

  <div class="col-lg-8">
    <div class="card">
      <div class="card-header bg-white fw-semibold d-flex justify-content-between align-items-center">
        <span><i class="bi bi-briefcase-fill text-success me-2"></i> My Job Applications</span>
        <a href="/jobs.php" class="btn btn-sm btn-success"><i class="bi bi-plus-circle"></i> Apply New</a>
      </div>

      <div class="card-body">
        <?php if ($apps->num_rows > 0): ?>
          <?php while ($app = $apps->fetch_assoc()): ?>
            <?php
              $appId = (int)$app['id'];
              $badgeClass = match($app['status']) {
                'Hired' => 'success', 'Interview' => 'info', 'Offer' => 'primary', 'Rejected' => 'danger', 'Screening' => 'warning', default => 'secondary'
              };

              // Fetch visible comments for this application
              $cStmt = $conn->prepare("
                SELECT c.*, u.name AS author_name
                FROM application_comments c
                JOIN users u ON u.id = c.user_id
                WHERE c.application_id=?
                  AND (c.visible_to_applicant=1 OR c.author_role='user')
                ORDER BY c.created_at ASC
              ");
              $cStmt->bind_param("i", $appId);
              $cStmt->execute();
              $comments = $cStmt->get_result();
              $cStmt->close();
            ?>
            <div class="application-item">
              <div class="d-flex justify-content-between flex-wrap align-items-start">
                <div>
                  <div class="app-title"><i class="bi bi-person-workspace me-1"></i> <?= e($app['position_name']) ?></div>
                  <div class="app-details">Applied: <?= e(date('M d, Y', strtotime($app['applied_at']))) ?> • Source: <?= e($app['source']) ?></div>
                </div>
                <div class="d-flex align-items-center gap-2">
                  <span class="badge bg-<?= $badgeClass ?>"><?= e($app['status']) ?></span>
                  <a class="btn btn-sm btn-outline-primary" href="/user/application_edit.php?id=<?= $appId ?>"><i class="bi bi-pencil-square"></i> Edit</a>
                  <form action="/user/application_delete.php" method="post" onsubmit="return confirm('Delete this application?');" class="m-0">
                    <input type="hidden" name="id" value="<?= $appId ?>">
                    <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i> Delete</button>
                  </form>
                </div>
              </div>

              <hr class="my-3">

              <div class="info-grid">
                <div><strong>Experience:</strong> <?= e($app['years_experience'] ?? '—') ?> yrs</div>
                <div><strong>Expected Salary:</strong> <?= e($app['expected_salary'] ? number_format($app['expected_salary']) . ' USD' : '—') ?></div>
                <div><strong>Resume:</strong> <?= e($app['cv_filename'] ?: 'N/A') ?></div>
                <div><strong>Status:</strong> <?= e($app['status']) ?></div>
              </div>

              <?php if (!empty($app['resume_path'])): ?>
                <div class="mt-2 text-end">
                  <a href="<?= e($app['resume_path']) ?>" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bi bi-file-earmark-arrow-down"></i> View Resume</a>
                </div>
              <?php endif; ?>

              <?php if (!empty($app['message'])): ?>
                <div class="mt-3"><strong>Cover Letter:</strong><br><?= nl2br(e($app['message'])) ?></div>
              <?php endif; ?>

              <div class="mt-4">
                <h6 class="fw-bold text-success"><i class="bi bi-chat-dots"></i> Comments</h6>
                <div>
                  <?php if ($comments->num_rows > 0): ?>
                    <?php while ($c = $comments->fetch_assoc()): ?>
                      <div class="comment-box <?= $c['author_role'] ?>" id="comment-<?= $c['id'] ?>">
                        <div class="d-flex justify-content-between align-items-start">
                          <div>
                            <div class="comment-author"><?= e($c['author_role'] === 'admin' ? 'Admin' : 'You') ?></div>
                            <div class="comment-date"><?= e(date('M d, Y H:i', strtotime($c['created_at']))) ?></div>
                          </div>
                          <?php if ($c['user_id'] == $uid): ?>
                            <div class="btn-group btn-group-sm">
                              <button class="btn btn-outline-primary" onclick="editComment(<?= $c['id'] ?>)"><i class="bi bi-pencil"></i></button>
                              <button class="btn btn-outline-danger" onclick="deleteComment(<?= $c['id'] ?>)"><i class="bi bi-trash"></i></button>
                            </div>
                          <?php endif; ?>
                        </div>
                        <div class="comment-content mt-2"><?= nl2br(e($c['comment'])) ?></div>
                      </div>
                    <?php endwhile; ?>
                  <?php else: ?>
                    <p class="text-muted small">No comments yet.</p>
                  <?php endif; ?>
                </div>

                <form class="comment-form mt-3" method="post" onsubmit="return submitComment(this, <?= $appId ?>);">
                  <textarea name="comment" class="form-control mb-2" placeholder="Write a comment for the hiring team..." required></textarea>
                  <button class="btn btn-sm btn-outline-success"><i class="bi bi-send"></i> Post Comment</button>
                </form>
              </div>
            </div>
          <?php endwhile; ?>
        <?php else: ?>
          <div class="text-center text-muted py-4">
            <i class="bi bi-folder2-open"></i><br>No applications yet.
          </div>
        <?php endif; ?>
      </div>
    </div>
  </div>
</div>

<script>
function toggleUploadForm() {
  const f = document.getElementById('uploadForm');
  f.style.display = (f.style.display === 'block') ? 'none' : 'block';
}

async function submitComment(form, appId) {
  const fd = new FormData(form);
  fd.append('application_id', appId);
  try {
    const res = await fetch('/user/comment_add.php', { method: 'POST', body: fd });
    if (res.ok) location.reload();
    else alert('Failed to post comment.');
  } catch (e) { alert('Network error while posting comment.'); }
  return false;
}

async function editComment(id) {
  const box = document.getElementById(`comment-${id}`);
  const contentEl = box.querySelector('.comment-content');
  const oldText = contentEl.innerText.trim();
  contentEl.innerHTML = `
    <textarea class='form-control mb-2'>${oldText}</textarea>
    <div class='edit-buttons'>
      <button class='btn btn-sm btn-success' onclick='saveComment(${id}, this)'><i class="bi bi-check-lg"></i> Save</button>
      <button class='btn btn-sm btn-secondary' onclick='location.reload()'>Cancel</button>
    </div>`;
}

async function saveComment(id, btn) {
  const textarea = btn.closest('.edit-buttons').previousElementSibling;
  const fd = new FormData();
  fd.append('id', id);
  fd.append('comment', textarea.value);
  const res = await fetch('/user/comment_edit.php', { method: 'POST', body: fd });
  if (res.ok) location.reload();
  else alert('Failed to update comment.');
}

async function deleteComment(id) {
  if (!confirm('Are you sure you want to delete this comment?')) return;
  const fd = new FormData();
  fd.append('id', id);
  const res = await fetch('/user/comment_delete.php', { method: 'POST', body: fd });
  if (res.ok) location.reload();
  else alert('Failed to delete comment.');
}
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>
