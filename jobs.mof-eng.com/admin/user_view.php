<?php
// /admin/user_view.php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';

// Safe helper for HTML escaping
if (!function_exists('e')) {
    function e($text) { return htmlspecialchars($text ?? '', ENT_QUOTES, 'UTF-8'); }
}

$page_title = "User Detailed Profile";
include __DIR__ . '/../includes/header.php';

$uid = (int)($_GET['id'] ?? 0);

// Fetch all fields from your users table
$stmt = $conn->prepare("SELECT * FROM users WHERE id = ? LIMIT 1");
$stmt->bind_param("i", $uid);
$stmt->execute();
$u = $stmt->get_result()->fetch_assoc();
$stmt->close();

if (!$u) {
    echo "<div class='container mt-5'><div class='alert alert-danger'>User not found.</div></div>";
    include __DIR__ . '/../includes/footer.php';
    exit;
}

// Fetch the latest application to show context
$app = $conn->query("SELECT ja.*, jp.position_name 
                     FROM job_applications ja 
                     LEFT JOIN job_positions jp ON jp.id = ja.position_id 
                     WHERE ja.user_id = $uid 
                     ORDER BY ja.applied_at DESC LIMIT 1")->fetch_assoc();
?>

<style>
    .resume-header { background: #fdfdfd; border-bottom: 2px solid #198754; padding: 30px 0; }
    .avatar-view { width: 130px; height: 130px; object-fit: cover; border: 5px solid #fff; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    .section-head { border-bottom: 2px solid #f0f0f0; margin-bottom: 15px; padding-bottom: 5px; color: #198754; font-weight: 700; text-transform: uppercase; font-size: 0.9rem; }
    .info-group { margin-bottom: 1rem; }
    .info-label { font-size: 0.75rem; color: #888; text-transform: uppercase; font-weight: 600; display: block; }
    .info-data { font-size: 1rem; color: #333; font-weight: 500; }
    .card { border: none; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
</style>

<div class="resume-header mb-4">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-md-auto text-center text-md-start">
                <?php 
                    $default = ($u['gender'] == 'female') ? '/uploads/profiles/default_female.png' : '/uploads/profiles/default_male.png';
                    $img = !empty($u['profile_photo_path']) ? $u['profile_photo_path'] : $default;
                ?>
                <img src="<?= e($img) ?>" class="rounded-circle avatar-view mb-3 mb-md-0">
            </div>
            <div class="col-md">
                <h1 class="fw-bold mb-1"><?= e($u['name']) ?></h1>
                <p class="text-muted mb-2"><i class="bi bi-envelope"></i> <?= e($u['email']) ?> | <i class="bi bi-phone"></i> <?= e($u['phone'] ?: 'No Phone') ?></p>
                <div class="d-flex gap-2">
                    <span class="badge bg-success">Role: <?= strtoupper($u['role']) ?></span>
                    <span class="badge bg-outline-secondary text-dark border">ID: #<?= $u['id'] ?></span>
                </div>
            </div>
            <div class="col-md-auto text-end">
                <a href="/admin/users.php" class="btn btn-light"><i class="bi bi-arrow-left"></i> Back</a>
            </div>
        </div>
    </div>
</div>

<div class="container">
    <div class="row">
        <div class="col-lg-4">
            <div class="card mb-4">
                <div class="card-body">
                    <div class="section-head">Personal Information</div>
                    
                    <div class="row">
                        <div class="col-6 info-group">
                            <span class="info-label">Gender</span>
                            <span class="info-data"><?= ucfirst(e($u['gender'] ?: '—')) ?></span>
                        </div>
                        <div class="col-6 info-group">
                            <span class="info-label">Age</span>
                            <span class="info-data"><?= e($u['age'] ?: '—') ?></span>
                        </div>
                    </div>

                    <div class="info-group">
                        <span class="info-label">Current Location</span>
                        <span class="info-data"><?= e($u['city']) ?>, <?= e($u['country']) ?></span>
                    </div>

                    <div class="info-group">
                        <span class="info-label">Full Address</span>
                        <span class="info-data"><?= e($u['address']) ?><br><?= e($u['address2']) ?></span>
                    </div>

                    <div class="section-head mt-4">Skills</div>
                    <div class="d-flex flex-wrap gap-1">
                        <?php 
                        $skills = explode(',', $u['skills'] ?? '');
                        foreach($skills as $s): if(trim($s)): ?>
                            <span class="badge bg-light text-dark border"><?= e(trim($s)) ?></span>
                        <?php endif; endforeach; ?>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-lg-8">
            <?php if($app): ?>
            <div class="alert alert-success border-0 shadow-sm d-flex justify-content-between align-items-center mb-4">
                <div>
                    <i class="bi bi-briefcase-fill me-2"></i>
                    Currently applying for: <strong><?= e($app['position_name']) ?></strong>
                </div>
                <span class="badge bg-white text-success"><?= e($app['status']) ?></span>
            </div>
            <?php endif; ?>

            <div class="card mb-4">
                <div class="card-body">
                    <div class="section-head"><i class="bi bi-mortarboard me-2"></i>Education History</div>
                    <div class="ms-2">
                        <h5 class="mb-1 fw-bold"><?= e($u['highest_degree'] ?: 'Degree Not Provided') ?></h5>
                        <p class="text-success mb-1"><?= e($u['institution']) ?></p>
                        <p class="text-muted small">Graduated: <?= e($u['graduation_year']) ?></p>
                    </div>
                </div>
            </div>

            <div class="card mb-4">
                <div class="card-body">
                    <div class="section-head"><i class="bi bi-briefcase me-2"></i>Professional Experience</div>
                    <div class="ms-2">
                        <h5 class="mb-1 fw-bold"><?= e($u['experience_title'] ?: 'Title Not Provided') ?></h5>
                        <p class="text-success mb-1"><?= e($u['experience_company']) ?></p>
                        <p class="text-muted small"><?= e($u['experience_years']) ?></p>
                        <div class="mt-3 p-3 bg-light rounded" style="white-space: pre-wrap; font-size: 0.95rem; line-height: 1.6;"><?= e($u['experience_description']) ?></div>
                    </div>
                </div>
            </div>

            <div class="text-center text-muted mt-4">
                <small>User Registered on: <?= date('F d, Y', strtotime($u['created_at'])) ?></small>
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/../includes/footer.php'; ?>