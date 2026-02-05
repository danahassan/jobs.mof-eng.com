<?php
// /admin/applications.php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';
require __DIR__ . '/../includes/helpers.php'; // for e() if you have it
$page_title = "Applications — View All & Manage";

/* ---------------------------
   Helpers
---------------------------- */
function get_status_badge_color($status) {
    return match ($status) {
        'Hired' => 'success',
        'Interview' => 'info',
        'Offer' => 'primary',
        'Screening' => 'warning',
        'Rejected' => 'danger',
        default => 'secondary', // New or anything else
    };
}
$ALLOWED_STATUSES = ['New','Screening','Interview','Offer','Hired','Rejected'];
$ALLOWED_SOURCES  = ['Website','LinkedIn','Referral','Walk-in','Other'];

/* ---------------------------
   Filters & Pagination
---------------------------- */
$q       = trim($_GET['q'] ?? '');
$status  = trim($_GET['status'] ?? '');      // one of $ALLOWED_STATUSES or ''
$source  = trim($_GET['source'] ?? '');      // one of $ALLOWED_SOURCES or ''
$page    = max(1, (int)($_GET['page'] ?? 1));
$perPage = 20;
$offset  = ($page - 1) * $perPage;

$where = [];
$args  = [];
$types = '';

if ($q !== '') {
    // match applicant name, email, or position name
    $where[] = "(u.name LIKE CONCAT('%', ?, '%') OR u.email LIKE CONCAT('%', ?, '%') OR p.position_name LIKE CONCAT('%', ?, '%'))";
    $args[] = $q; $args[] = $q; $args[] = $q;
    $types .= 'sss';
}
if ($status !== '' && in_array($status, $ALLOWED_STATUSES, true)) {
    $where[] = "a.status = ?";
    $args[]  = $status;
    $types  .= 's';
}
if ($source !== '' && in_array($source, $ALLOWED_SOURCES, true)) {
    $where[] = "a.source = ?";
    $args[]  = $source;
    $types  .= 's';
}

$whereSql = $where ? ('WHERE ' . implode(' AND ', $where)) : '';

/* ---------------------------
   Count (for pagination)
---------------------------- */
$countSql = "
  SELECT COUNT(*) AS c
  FROM job_applications a
  LEFT JOIN users u ON u.id = a.user_id
  LEFT JOIN job_positions p ON p.id = a.position_id
  $whereSql
";
$countStmt = $conn->prepare($countSql);
if ($types !== '') $countStmt->bind_param($types, ...$args);
$countStmt->execute();
$countRes = $countStmt->get_result();
$total    = (int)($countRes->fetch_assoc()['c'] ?? 0);
$countStmt->close();

$totalPages = max(1, (int)ceil($total / $perPage));

/* ---------------------------
   Fetch paginated results
---------------------------- */
$listSql = "
  SELECT
    a.id, a.status, a.applied_at, a.source,
    u.name AS applicant_name, u.email,
    p.position_name
  FROM job_applications a
  LEFT JOIN users u ON u.id = a.user_id
  LEFT JOIN job_positions p ON p.id = a.position_id
  $whereSql
  ORDER BY a.applied_at DESC
  LIMIT ? OFFSET ?
";
$listStmt = $conn->prepare($listSql);
if ($types !== '') {
    $typesLimit = $types . 'ii';
    $bindArgs   = array_merge($args, [$perPage, $offset]);
    $listStmt->bind_param($typesLimit, ...$bindArgs);
} else {
    $listStmt->bind_param('ii', $perPage, $offset);
}
$listStmt->execute();
$res  = $listStmt->get_result();
$rows = [];
while ($r = $res->fetch_assoc()) $rows[] = $r;
$listStmt->close();

include __DIR__ . '/../includes/header.php';
?>
<style>
  .filter-chip { background:#f8f9fa; border:1px solid #e9ecef; border-radius:.5rem; padding:.5rem .75rem; }
  .table td, .table th { vertical-align: middle; }
  .badge.rounded-pill { font-weight:600; }
  .status-select { min-width: 9rem; }
</style>

<h3 class="fw-bold mb-3">Applications — View All & Manage</h3>

<!-- Filters -->
<form class="row g-2 align-items-end mb-3" method="get">
  <div class="col-md-4">
    <label class="form-label">Search</label>
    <input type="text" class="form-control" name="q" value="<?= e($q) ?>" placeholder="Name, email, or position">
  </div>
  <div class="col-md-3">
    <label class="form-label">Status</label>
    <select name="status" class="form-select">
      <option value="">All</option>
      <?php foreach ($ALLOWED_STATUSES as $s): ?>
        <option value="<?= e($s) ?>" <?= $status===$s?'selected':'' ?>><?= e($s) ?></option>
      <?php endforeach; ?>
    </select>
  </div>
  <div class="col-md-3">
    <label class="form-label">Source</label>
    <select name="source" class="form-select">
      <option value="">All</option>
      <?php foreach ($ALLOWED_SOURCES as $s): ?>
        <option value="<?= e($s) ?>" <?= $source===$s?'selected':'' ?>><?= e($s) ?></option>
      <?php endforeach; ?>
    </select>
  </div>
  <div class="col-md-2">
    <button class="btn btn-primary w-100"><i class="bi bi-search"></i> Filter</button>
  </div>
</form>

<!-- Active filters summary -->
<?php if ($q!=='' || $status!=='' || $source!==''): ?>
  <div class="mb-3 small">
    <span class="me-2">Active filters:</span>
    <?php if ($q!==''): ?><span class="filter-chip me-1">q: "<?= e($q) ?>"</span><?php endif; ?>
    <?php if ($status!==''): ?><span class="filter-chip me-1">status: <?= e($status) ?></span><?php endif; ?>
    <?php if ($source!==''): ?><span class="filter-chip me-1">source: <?= e($source) ?></span><?php endif; ?>
    <a href="/admin/applications.php" class="ms-2 text-decoration-none">Clear</a>
  </div>
<?php endif; ?>

<div class="card shadow-sm">
  <div class="card-header bg-white fw-semibold">Results (<?= number_format($total) ?>)</div>
  <div class="card-body p-0">
    <?php if (count($rows) > 0): ?>
      <div class="table-responsive">
        <table class="table table-striped table-hover align-middle mb-0">
          <thead class="table-secondary">
            <tr>
              <th style="width:70px">#</th>
              <th>Applicant</th>
              <th>Position</th>
              <th>Applied</th>
              <th>Source</th>
              <th>Status</th>
              <th style="width:210px">Actions</th>
            </tr>
          </thead>
          <tbody>
            <?php foreach ($rows as $row): ?>
              <?php $badge = get_status_badge_color($row['status']); ?>
              <tr id="app-row-<?= (int)$row['id'] ?>">
                <td><?= (int)$row['id'] ?></td>
                <td>
                  <div class="fw-semibold"><?= e($row['applicant_name'] ?? '—') ?></div>
                  <div class="text-muted small"><?= e($row['email'] ?? '') ?></div>
                </td>
                <td><?= e($row['position_name'] ?? '—') ?></td>
                <td class="text-muted"><?= $row['applied_at'] ? date('M d, Y', strtotime($row['applied_at'])) : '—' ?></td>
                <td><span class="badge bg-light text-dark"><?= e($row['source'] ?? '—') ?></span></td>
                <td>
                  <div class="d-flex align-items-center gap-2">
                    <span class="badge rounded-pill text-bg-<?= $badge ?>"><?= e($row['status']) ?></span>
                    <select class="form-select form-select-sm status-select"
                            data-id="<?= (int)$row['id'] ?>"
                            onchange="updateStatus(this)">
                      <?php foreach ($ALLOWED_STATUSES as $s): ?>
                        <option value="<?= e($s) ?>" <?= $row['status']===$s ? 'selected':'' ?>><?= e($s) ?></option>
                      <?php endforeach; ?>
                    </select>
                  </div>
                </td>
                <td>
                  <div class="d-flex gap-2">
                    <a href="/admin/application_detail.php?id=<?= (int)$row['id'] ?>" class="btn btn-sm btn-outline-secondary">
                      <i class="bi bi-eye"></i> View
                    </a>
                    <form action="/admin/delete_application.php" method="post"
                          onsubmit="return confirm('Delete application #<?= (int)$row['id'] ?>?');" class="m-0">
                      <input type="hidden" name="id" value="<?= (int)$row['id'] ?>">
                      <button class="btn btn-sm btn-outline-danger">
                        <i class="bi bi-trash"></i> Delete
                      </button>
                    </form>
                  </div>
                </td>
              </tr>
            <?php endforeach; ?>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <nav class="p-3">
        <ul class="pagination mb-0">
          <?php
            // preserve filters in links
            $base = '/admin/applications.php?'
                  . http_build_query(array_filter([
                      'q' => $q,
                      'status' => $status,
                      'source' => $source
                    ]));
            $prev = max(1, $page-1);
            $next = min($totalPages, $page+1);
          ?>
          <li class="page-item <?= $page<=1?'disabled':'' ?>">
            <a class="page-link" href="<?= $base . '&page=' . $prev ?>">«</a>
          </li>
          <?php
            // show compact page range
            $start = max(1, $page-2);
            $end   = min($totalPages, $page+2);
            for ($i=$start; $i<=$end; $i++):
          ?>
            <li class="page-item <?= $i===$page?'active':'' ?>">
              <a class="page-link" href="<?= $base . '&page=' . $i ?>"><?= $i ?></a>
            </li>
          <?php endfor; ?>
          <li class="page-item <?= $page>=$totalPages?'disabled':'' ?>">
            <a class="page-link" href="<?= $base . '&page=' . $next ?>">»</a>
          </li>
        </ul>
      </nav>
    <?php else: ?>
      <div class="p-5 text-center text-muted">No applications found for the current filters.</div>
    <?php endif; ?>
  </div>
</div>

<script>
async function updateStatus(sel){
  const id = sel.dataset.id;
  const status = sel.value;
  sel.disabled = true;

  try {
    const res = await fetch('/admin/update_status.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `application_id=${encodeURIComponent(id)}&status=${encodeURIComponent(status)}`
    });
    const data = await res.json().catch(()=>({ok:false,error:'Invalid response'}));

    if (res.ok && data.ok) {
      // update badge text and style
      const row = document.getElementById('app-row-'+id);
      if (row) {
        const badge = row.querySelector('.badge.rounded-pill');
        if (badge) {
          badge.textContent = status;
          // map to bootstrap contextual color (same logic as PHP)
          const toColor = {
            'Hired':'success',
            'Interview':'info',
            'Offer':'primary',
            'Screening':'warning',
            'Rejected':'danger'
          }[status] || 'secondary';
          badge.className = 'badge rounded-pill text-bg-' + toColor;
        }
      }
    } else {
      alert('Failed to update status' + (data.error ? (': ' + data.error) : ''));
      // revert select to previous on error
      sel.value = sel.getAttribute('data-prev') || sel.value;
    }
  } catch (e) {
    alert('Network error while updating status.');
  } finally {
    sel.disabled = false;
    sel.setAttribute('data-prev', status);
  }
}
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>
