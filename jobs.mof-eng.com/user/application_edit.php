<?php
// /user/application_edit.php
require __DIR__ . '/../includes/helpers.php';
require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';
require __DIR__ . '/../includes/header.php';

$app_id = (int)($_GET['id'] ?? 0);
$uid    = (int)($_SESSION['user_id'] ?? 0);

// Load application (must belong to user)
$stmt = $conn->prepare("
  SELECT a.*, p.position_name
  FROM job_applications a
  JOIN job_positions p ON p.id = a.position_id
  WHERE a.id=? AND a.user_id=?
  LIMIT 1
");
$stmt->bind_param("ii", $app_id, $uid);
$stmt->execute();
$app = $stmt->get_result()->fetch_assoc();
$stmt->close();

if (!$app) {
  echo '<div class="alert alert-danger mt-4">Application not found or access denied.</div>';
  include __DIR__ . '/../includes/footer.php';
  exit;
}

// Load active positions (if you want to let user change position)
$posRes = $conn->query("SELECT id, position_name FROM job_positions WHERE status='active' ORDER BY position_name ASC");
?>
<style>
.container-xl, .container-lg, .container-md, .container-sm { max-width: 1100px; }
.card { border-radius: 12px; box-shadow: 0 6px 16px rgba(0,0,0,0.06); }
</style>

<div class="container mt-4">
  <div class="card">
    <div class="card-header bg-white">
      <h5 class="mb-0 text-success"><i class="bi bi-pencil-square me-1"></i> Edit Application</h5>
    </div>

    <div class="card-body">
      <form method="post" action="/user/application_update.php" enctype="multipart/form-data" class="row g-3">
        <input type="hidden" name="id" value="<?= (int)$app['id'] ?>">

        <div class="col-md-6">
          <label class="form-label fw-semibold">Position</label>
          <select name="position_id" class="form-select" required>
            <?php while ($p = $posRes->fetch_assoc()): ?>
              <option value="<?= (int)$p['id'] ?>" <?= ((int)$p['id'] === (int)$app['position_id'] ? 'selected' : '') ?>>
                <?= e($p['position_name']) ?>
              </option>
            <?php endwhile; ?>
          </select>
        </div>

        <div class="col-md-3">
          <label class="form-label fw-semibold">Experience (years)</label>
          <input type="number" min="0" name="years_experience" class="form-control" value="<?= e($app['years_experience']) ?>">
        </div>

        <div class="col-md-3">
          <label class="form-label fw-semibold">Expected Salary (USD)</label>
          <input type="number" step="0.01" min="0" name="expected_salary" class="form-control" value="<?= e($app['expected_salary']) ?>">
        </div>

        <div class="col-md-6">
          <label class="form-label fw-semibold">Source</label>
          <select name="source" class="form-select" required>
            <?php
              $sources = ['Website','LinkedIn','Referral','Walk-in','Other'];
              foreach ($sources as $src) {
                $sel = ($app['source'] == $src) ? 'selected' : '';
                echo "<option value='".e($src)."' $sel>".e($src)."</option>";
              }
            ?>
          </select>
        </div>

        <div class="col-md-6">
          <label class="form-label fw-semibold">Upload New CV (optional)</label>
          <input type="file" name="cv" class="form-control" accept=".pdf,.doc,.docx">
          <?php if (!empty($app['cv_filename'])): ?>
            <small class="text-muted">Current: <?= e($app['cv_filename']) ?></small>
          <?php endif; ?>
        </div>

        <div class="col-12">
          <label class="form-label fw-semibold">Cover Letter / Message</label>
          <textarea name="message" class="form-control" rows="5" placeholder="Write a message to hiring team..."><?= e($app['message']) ?></textarea>
        </div>

        <div class="col-12 d-flex gap-2">
          <a href="/user/dashboard.php" class="btn btn-outline-secondary"><i class="bi bi-arrow-left"></i> Back</a>
          <button class="btn btn-success"><i class="bi bi-save"></i> Save Changes</button>
        </div>
      </form>
    </div>
  </div>
</div>

<?php include __DIR__ . '/../includes/footer.php'; ?>
