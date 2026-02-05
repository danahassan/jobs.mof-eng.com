<?php
if (session_status() === PHP_SESSION_NONE) session_start();
$current_page = basename($_SERVER['PHP_SELF']);
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?= $page_title ?? 'MOF-ENG Jobs Portal' ?></title>

  <!-- Favicon -->
  <link rel="icon" href="https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png" type="image/png">

  <!-- Bootstrap & Icons -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">

  <style>
    html, body {
      height: 100%;
      margin: 0;
      display: flex;
      flex-direction: column;
      background-color: #f5f7fb;
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Navbar */
    .navbar {
      background: #ffffff;
      border-bottom: 1px solid #dee2e6;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .navbar-brand img {
      height: 46px;
      margin-right: 10px;
    }
    .navbar-brand span {
      color: #198754; /* green */
      font-weight: 700;
      font-size: 1.05rem;
    }
    .nav-link {
      color: #198754 !important;
      font-weight: bold;
      margin: 0 0.5rem;
      border-radius: 0.5rem;
      transition: background-color 0.2s ease;
    }
    .nav-link:hover, .nav-link.active {
      background-color: #e9f7ef;
      color: #198754 !important;
    }
    .nav-link.logout:hover {
      background-color: #f8d7da !important;
      color: #dc3545 !important;
    }

    /* Page Wrapper */
    .page-wrapper {
      flex: 1;
      max-width: 1140px;
      width: 100%;
      margin: 2rem auto;
      padding: 2rem;
      background: #ffffff;
      border-radius: 0.75rem;
      box-shadow: 0 2px 10px rgba(0,0,0,0.05);
      border: 1px solid #e9ecef;
    }

    footer {
      margin-top: auto;
      background: #ffffff;
      border-top: 1px solid #dee2e6;
      color: #555;
    }

    .avatar {
      width: 84px;
      height: 84px;
      border-radius: 50%;
      object-fit: cover;
      border: 2px solid #e9ecef;
    }
  </style>
</head>
<body>

<!-- 🌐 Unified Navbar -->
<nav class="navbar navbar-expand-lg navbar-light shadow-sm sticky-top">
  <div class="container-fluid" style="max-width:1140px;">
    <a class="navbar-brand d-flex align-items-center" href="/index.php">
      <img src="https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png" alt="MOF Logo">
      <span>Managing Of Future Eng. Company</span>
    </a>

    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"
            aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <div class="collapse navbar-collapse justify-content-end" id="navbarNav">
      <ul class="navbar-nav mb-2 mb-lg-0">

        <!-- 👑 Admin Menu -->
        <?php if (!empty($_SESSION['role']) && $_SESSION['role'] === 'admin'): ?>
          <li class="nav-item">
            <a class="nav-link <?= $current_page=='dashboard.php'?'active':'' ?>" href="/admin/dashboard.php">Dashboard</a>
          </li>
          <li class="nav-item">
            <a class="nav-link <?= $current_page=='positions.php'?'active':'' ?>" href="/admin/positions.php">Positions</a>
          </li>
          <!-- 🧍 Users (only for admins) -->
          <li class="nav-item">
            <a class="nav-link <?= $current_page=='users.php'?'active':'' ?>" href="/admin/users.php">Users</a>
          </li>
        <?php endif; ?>

        <!-- 👤 User Dashboard (non-admin) -->
        <?php if (!empty($_SESSION['role']) && $_SESSION['role'] === 'user'): ?>
          <li class="nav-item">
            <a class="nav-link <?= $current_page=='dashboard.php'?'active':'' ?>" href="/user/dashboard.php">Dashboard</a>
          </li>
        <?php endif; ?>

        <!-- 🧳 Jobs (only for logged-in, non-admin users) -->
        <?php if (!empty($_SESSION['user_id']) && (!isset($_SESSION['role']) || $_SESSION['role'] !== 'admin')): ?>
          <li class="nav-item">
            <a class="nav-link <?= $current_page=='jobs.php'?'active':'' ?>" href="/jobs.php">Jobs</a>
          </li>
        <?php endif; ?>

        <!-- 🌍 Contact & About (visible to everyone) -->
        <li class="nav-item">
          <a class="nav-link <?= $current_page=='contact.php'?'active':'' ?>" href="/contact.php">Contact</a>
        </li>
        <li class="nav-item">
          <a class="nav-link <?= $current_page=='about.php'?'active':'' ?>" href="/about.php">About</a>
        </li>

        <!-- 🔐 Auth -->
        <?php if (!empty($_SESSION['user_id'])): ?>
          <li class="nav-item">
            <a class="nav-link logout" href="/auth/logout.php">Logout</a>
          </li>
        <?php else: ?>
          <?php if ($current_page !== 'login.php'): ?>
            <li class="nav-item">
              <a class="nav-link <?= $current_page=='login.php'?'active':'' ?>" href="/auth/login.php">Login</a>
            </li>
          <?php endif; ?>
        <?php endif; ?>

      </ul>
    </div>
  </div>
</nav>

<!-- 🧩 Page Wrapper -->
<div class="page-wrapper">
