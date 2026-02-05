<?php
// 1. Handle logic and potential redirects BEFORE any HTML output
if (session_status() === PHP_SESSION_NONE) session_start();
require __DIR__ . '/../db.php';

$err = '';
$page_title = "Login";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $identifier = trim($_POST['identifier']); // May be email or phone
    $pass = $_POST['password'];

    if (empty($identifier) || empty($pass)) {
        $err = "Please enter your email or phone and password.";
    } else {
        if (filter_var($identifier, FILTER_VALIDATE_EMAIL)) {
            $q = $conn->prepare("SELECT * FROM users WHERE email=? LIMIT 1");
        } else {
            $q = $conn->prepare("SELECT * FROM users WHERE phone=? LIMIT 1");
        }

        $q->bind_param("s", $identifier);
        $q->execute();
        $res = $q->get_result();

        if ($u = $res->fetch_assoc()) {
            if (password_verify($pass, $u['password_hash'])) {
                $_SESSION['user_id'] = (int)$u['id'];
                $_SESSION['role'] = $u['role'];
                
                // Redirect happens here - now it will work because no HTML has been sent yet
                header("Location: " . ($u['role'] === 'admin' ? "/admin/dashboard.php" : "/user/dashboard.php"));
                exit;
            }
        }

        $err = "Invalid credentials. Please check your email/phone and password.";
    }
}

// 2. NOW include the header, after all possible redirects
include __DIR__ . '/../includes/header.php';
?>

<style>
  body {
    background: linear-gradient(135deg, #f0f4f8, #e9f7ef);
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  }
  .login-card {
    border: none;
    border-radius: 16px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    background-color: #fff;
    overflow: hidden;
  }
  .form-label {
    font-weight: 600;
    color: #333;
  }
  .form-control {
    border-radius: 8px;
  }
  .btn-primary {
    background-color: #198754;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s ease-in-out;
  }
  .btn-primary:hover {
    background-color: #157347;
  }
  .logo-top {
    max-width: 180px;
    height: auto;
    margin-bottom: 1rem;
  }
</style>

<div class="container my-5">
  <div class="row justify-content-center">
    <div class="col-lg-6 col-md-8 col-sm-10">

      <div class="card login-card p-4">
        <div class="card-body text-center">
          <img src="https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png"
               alt="MOF-ENG Logo"
               class="logo-top">

          <h3 class="fw-bold mb-4 text-success">Login to Jobs Portal</h3>

          <?php if ($err): ?>
            <div class="alert alert-danger text-center" role="alert">
              <?= htmlspecialchars($err) ?>
            </div>
          <?php endif; ?>

          <form method="post">
            <div class="mb-3 text-start">
              <label for="identifier" class="form-label">Email or Mobile Number</label>
              <input type="text" id="identifier" name="identifier"
                     class="form-control"
                     placeholder="Email or phone number"
                     value="<?= htmlspecialchars($_POST['identifier'] ?? '') ?>" required>
            </div>

            <div class="mb-4 text-start">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <label for="password" class="form-label mb-0">Password</label>
                <a href="/auth/forgot_password.php" class="text-success small fw-bold" style="text-decoration: none;">Forgot Password?</a>
              </div>
              <div class="input-group">
                <input type="password" id="password" name="password"
                       class="form-control"
                       placeholder="Enter your password" required>
                <button type="button" class="btn btn-outline-secondary" id="togglePassword">
                  <i class="bi bi-eye"></i>
                </button>
              </div>
            </div>

            <div class="d-grid gap-2">
              <button class="btn btn-primary btn-lg" type="submit">Login</button>
            </div>
          </form>
        </div>
      </div>

      <p class="text-center mt-3">
        Don’t have an account? <a href="/auth/register.php" class="fw-bold text-success">Register here</a>
      </p>

    </div>
  </div>
</div>

<script>
document.getElementById('togglePassword').addEventListener('click', function () {
  const passwordField = document.getElementById('password');
  const icon = this.querySelector('i');
  const isHidden = passwordField.type === 'password';
  passwordField.type = isHidden ? 'text' : 'password';
  icon.classList.toggle('bi-eye');
  icon.classList.toggle('bi-eye-slash');
});
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>