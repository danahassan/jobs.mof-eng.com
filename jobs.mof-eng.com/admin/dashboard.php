<?php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';
$page_title = "Admin Dashboard";

/* ---------------------------
   🔹 Dashboard Data Logic
---------------------------- */
function fetch_count($conn, $query) {
    $result = $conn->query($query);
    return (int)($result->fetch_assoc()['c'] ?? 0);
}

$k_total      = fetch_count($conn, "SELECT COUNT(*) c FROM job_applications");
$k_7d         = fetch_count($conn, "SELECT COUNT(*) c FROM job_applications WHERE applied_at >= (NOW() - INTERVAL 7 DAY)");
$k_hired      = fetch_count($conn, "SELECT COUNT(*) c FROM job_applications WHERE status='Hired'");
$k_interview  = fetch_count($conn, "SELECT COUNT(*) c FROM job_applications WHERE status='Interview'");

/* ✅ Updated: Use alias for status to avoid overwriting */
$applications_query = "
    SELECT 
        a.id, 
        a.status AS app_status, 
        a.applied_at, 
        u.name AS applicant_name,
        p.position_name
    FROM job_applications a
    LEFT JOIN users u ON u.id = a.user_id
    LEFT JOIN job_positions p ON p.id = a.position_id
    ORDER BY a.applied_at DESC
    LIMIT 10
";
$applications_result = $conn->query($applications_query);
$applications = [];
if ($applications_result) {
    while ($row = $applications_result->fetch_assoc()) {
        $applications[] = $row;
    }
}

include __DIR__ . '/../includes/header.php';

/* ---------------------------
   🎨 Helper: Badge Color
---------------------------- */
function get_status_badge_color($status) {
    return match ($status) {
        'Hired' => 'success',
        'Interview' => 'info',
        'Offer' => 'primary',
        'Screening' => 'warning',
        'Rejected' => 'danger',
        default => 'secondary',
    };
}
?>

<style>
/* 🎨 Enhanced Styles for Dashboard Cards */
.metric-card {
  border-radius: 0.75rem;
  transition: transform 0.2s ease-in-out;
}
.metric-card:hover {
  transform: translateY(-4px);
}
.list-card {
  border-radius: 0.75rem;
  overflow: hidden;
}
.list-card-header {
  background: #f8f9fa;
  font-weight: 600;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e9ecef;
}
.list-group-item {
  border: none !important;
  border-bottom: 1px solid #f1f1f1 !important;
}
.list-group-item:last-child {
  border-bottom: none !important;
}
.list-group-item span.badge {
  font-size: 1rem;
}
.card-gradient {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
}
.card-gradient-info {
  background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
}
.card-gradient-warning {
  background: linear-gradient(135deg, #ffc107 0%, #ffb300 100%);
}
.card-gradient-success {
  background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
}
</style>

<h3 class="fw-bold mb-4">Admin Dashboard</h3>

<!-- KPI CARDS -->
<div class="row g-4 mb-5">
  <div class="col-sm-6 col-lg-3">
    <div class="card metric-card text-white shadow-sm border-0 card-gradient">
      <div class="card-body text-center py-4">
        <h6 class="fw-semibold">Total Applications</h6>
        <h2 class="fw-bolder display-6"><?= $k_total ?></h2>
        <p class="small opacity-75 mb-0">All received applications</p>
      </div>
    </div>
  </div>

  <div class="col-sm-6 col-lg-3">
    <div class="card metric-card text-white shadow-sm border-0 card-gradient-info">
      <div class="card-body text-center py-4">
        <h6 class="fw-semibold">New (7d)</h6>
        <h2 class="fw-bolder display-6"><?= $k_7d ?></h2>
        <p class="small opacity-75 mb-0">Applications in last 7 days</p>
      </div>
    </div>
  </div>

  <div class="col-sm-6 col-lg-3">
    <div class="card metric-card shadow-sm border-0 card-gradient-warning">
      <div class="card-body text-center py-4 text-dark">
        <h6 class="fw-semibold">Interview Stage</h6>
        <h2 class="fw-bolder display-6"><?= $k_interview ?></h2>
        <p class="small opacity-75 mb-0">Currently under interview</p>
      </div>
    </div>
  </div>

  <div class="col-sm-6 col-lg-3">
    <div class="card metric-card text-white shadow-sm border-0 card-gradient-success">
      <div class="card-body text-center py-4">
        <h6 class="fw-semibold">Hired</h6>
        <h2 class="fw-bolder display-6"><?= $k_hired ?></h2>
        <p class="small opacity-75 mb-0">Successfully hired applicants</p>
      </div>
    </div>
  </div>
</div>

<!-- 🎯 Applications Breakdown Section -->
<div class="row g-4 mb-5">
  <div class="col-lg-6">
    <div class="card list-card shadow-sm">
      <div class="list-card-header bg-primary text-white d-flex align-items-center justify-content-between">
        <span><i class="bi bi-bar-chart-line"></i> Applications By Status</span>
        <i class="bi bi-people"></i>
      </div>
      <div class="card-body p-0">
        <div id="by_status" class="p-3"></div>
      </div>
    </div>
  </div>

  <div class="col-lg-6">
    <div class="card list-card shadow-sm">
      <div class="list-card-header bg-success text-white d-flex align-items-center justify-content-between">
        <span><i class="bi bi-globe2"></i> Applications By Source</span>
        <i class="bi bi-diagram-3"></i>
      </div>
      <div class="card-body p-0">
        <div id="by_source" class="p-3"></div>
      </div>
    </div>
  </div>
</div>

<!-- 🧾 Latest Applications Table -->
<div class="card shadow-lg">
  <div class="card-header text-bg-dark fw-bold d-flex justify-content-between align-items-center py-3">
    Latest 10 Applications
    <a href="/admin/applications.php" class="btn btn-sm btn-outline-light fw-bold">
      View All & Manage <i class="bi bi-arrow-right"></i>
    </a>
  </div>
  <div class="card-body p-0">
    <?php if (!empty($applications)): ?>
      <div class="table-responsive">
        <table class="table table-striped table-hover align-middle mb-0">
          <thead class="table-secondary">
            <tr>
              <th>#</th>
              <th>Applicant</th>
              <th>Position</th>
              <th>Applied At</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <?php foreach ($applications as $app): ?>
            <tr>
              <th scope="row"><?= $app['id'] ?></th>
              <td><?= htmlspecialchars($app['applicant_name'] ?? '—') ?></td>
              <td><?= htmlspecialchars($app['position_name'] ?? '—') ?></td>
              <td class="text-muted"><?= date('M d, Y', strtotime($app['applied_at'])) ?></td>
              <td>
                <span class="badge text-bg-<?= get_status_badge_color($app['app_status']) ?> rounded-pill py-2 px-3">
                  <?= htmlspecialchars($app['app_status'] ?: 'Pending') ?>
                </span>
              </td>
              <td>
                <a href="/admin/application_detail.php?id=<?= $app['id'] ?>" class="btn btn-sm btn-outline-secondary">
                  <i class="bi bi-arrow-right-short"></i> View
                </a>
              </td>
            </tr>
            <?php endforeach; ?>
          </tbody>
        </table>
      </div>
    <?php else: ?>
      <div class="p-5 text-center text-muted">No recent applications found.</div>
    <?php endif; ?>
  </div>
</div>

<!-- 📊 JavaScript to Render Lists -->
<script>
(async ()=>{
  const res = await fetch('/admin_stats.php');
  const d = await res.json();

  function listToUl(id, labels, values){
    let html = '<ul class="list-group list-group-flush">';
    for(let i=0;i<labels.length;i++){
      html += `
        <li class="list-group-item d-flex justify-content-between align-items-center py-3">
          <span class="fw-medium">
            <i class="bi bi-caret-right-fill text-secondary"></i> ${labels[i]}
          </span>
          <span class="badge bg-dark rounded-pill fs-6 px-3 py-2">${values[i]}</span>
        </li>`;
    }
    html += '</ul>';
    document.getElementById(id).innerHTML = html;
  }

  if (d.by_status && d.by_source) {
    listToUl('by_status', d.by_status.labels, d.by_status.values);
    listToUl('by_source', d.by_source.labels, d.by_source.values);
  }
})();
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>
