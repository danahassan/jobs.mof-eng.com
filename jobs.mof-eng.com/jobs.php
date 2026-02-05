<?php
ini_set('display_errors', 1);
error_reporting(E_ALL);

// jobs.php — Job Listings Grid Page

require __DIR__ . '/includes/auth_user.php';
require __DIR__ . '/db.php';
require __DIR__ . '/includes/helpers.php';

$page_title = "Available Jobs";
include __DIR__ . '/includes/header.php';

// ✅ Fetch active positions with location + employment_type
$stmt = $conn->prepare("
    SELECT id, position_name, quantity, status, location, employment_type, description, created_at
    FROM job_positions
    WHERE status='active'
    ORDER BY id DESC
");
$stmt->execute();
$positions = $stmt->get_result();
?>
<style>
body {
  background-color: #f4f7fb;
}
.jobs-container {
  max-width: 1200px;
  margin: 3rem auto 4rem;
}
.jobs-header {
  text-align: center;
  margin-bottom: 2.5rem;
}
.jobs-header h2 {
  font-weight: 800;
  color: #198754;
  margin-bottom: .5rem;
}
.jobs-header p {
  color: #666;
  font-size: 1rem;
}
.job-card {
  background: #fff;
  border: 1px solid #e1e4e8;
  border-radius: .75rem;
  padding: 1.5rem;
  transition: all .25s ease-in-out;
  height: 100%;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}
.job-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 14px rgba(0,0,0,0.1);
}
.job-title {
  color: #0d6efd;
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: .4rem;
}
.job-meta {
  color: #666;
  font-size: .9rem;
  margin-bottom: .8rem;
}
.job-desc {
  font-size: .9rem;
  color: #444;
  min-height: 65px;
  margin-bottom: 1rem;
}
.apply-btn {
  background: #198754;
  color: #fff;
  border: none;
  padding: .55rem 1.2rem;
  border-radius: .4rem;
  text-decoration: none;
  font-weight: 600;
  display: inline-block;
  transition: background .2s ease;
}
.apply-btn:hover {
  background: #146c43;
  color: #fff;
}
.badge-light {
  background: #e9f7ef;
  color: #198754;
  font-weight: 500;
}
</style>

<div class="jobs-container">
  <div class="jobs-header">
    <h2><i class="bi bi-briefcase-fill text-success me-2"></i>Available Job Openings</h2>
    <p>Browse and apply to the latest opportunities at <strong>MANAGING OF FUTURE ENG. (MOF) COMPANY</strong></p>
  </div>

  <?php if ($positions->num_rows > 0): ?>
    <div class="row g-4">
      <?php while ($pos = $positions->fetch_assoc()): ?>
        <div class="col-md-6 col-lg-4 d-flex">
          <div class="job-card flex-fill d-flex flex-column justify-content-between">
            <div>
              <div class="job-title">
                <i class="bi bi-person-workspace me-1"></i> <?= e($pos['position_name']) ?>
              </div>

              <div class="job-meta">
                <i class="bi bi-calendar-event text-success me-1"></i>
                <?= !empty($pos['created_at']) ? e(date('M d, Y', strtotime($pos['created_at']))) : '—' ?>
                &nbsp;|&nbsp;
                <i class="bi bi-people-fill text-success me-1"></i>
                Openings: <?= e($pos['quantity'] ?? 1) ?>
              </div>

              <?php if (!empty($pos['description'])): ?>
                <div class="job-desc">
                  <?= nl2br(e(strlen($pos['description']) > 150 ? substr($pos['description'], 0, 150) . '...' : $pos['description'])) ?>
                </div>
              <?php endif; ?>
            </div>

            <div>
              <div class="mb-2">
                <?php if (!empty($pos['location'])): ?>
                  <span class="badge badge-light me-1">
                    <i class="bi bi-geo-alt me-1"></i> <?= e($pos['location']) ?>
                  </span>
                <?php endif; ?>
                <span class="badge badge-light">
                  <i class="bi bi-clock-history me-1"></i> <?= e(ucwords($pos['employment_type'] ?? 'Full time')) ?>
                </span>
              </div>

              <a href="/apply.php?position_id=<?= e($pos['id']) ?>" class="apply-btn w-100">
                <i class="bi bi-send-check me-1"></i> Apply Now
              </a>
            </div>
          </div>
        </div>
      <?php endwhile; ?>
    </div>
  <?php else: ?>
    <div class="text-center text-muted py-5">
      <i class="bi bi-folder2-open display-4 d-block mb-3"></i>
      <p class="mb-0">No job openings available right now.</p>
      <p class="text-muted">Please check back soon for new positions.</p>
    </div>
  <?php endif; ?>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>
