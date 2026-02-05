<?php
// /user/profile_edit.php
require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';
require __DIR__ . '/../includes/helpers.php';

$page_title = "Edit Profile";
include __DIR__ . '/../includes/header.php';

$uid = (int)($_SESSION['user_id'] ?? 0);

$stmt = $conn->prepare("SELECT * FROM users WHERE id=? LIMIT 1");
$stmt->bind_param("i", $uid);
$stmt->execute();
$user = $stmt->get_result()->fetch_assoc();
$stmt->close();

if (!$user) {
    echo '<div class="alert alert-danger mt-4 shadow-sm">User not found or session expired.</div>';
    include __DIR__ . '/../includes/footer.php';
    exit;
}

$selected = function($value, $current) {
    return (string)$value === (string)$current ? 'selected' : '';
};

// Comprehensive list of countries
$countries = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan",
    "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi",
    "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic",
    "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia",
    "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
    "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan",
    "Kazakhstan", "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
    "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar",
    "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway", "Oman",
    "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar",
    "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria",
    "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu",
    "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam",
    "Yemen", "Zambia", "Zimbabwe"
];
?>
<style>
.container-xl, .container-lg, .container-md, .container-sm { max-width: 1200px; }
.profile-card { border: none; border-radius: 14px; box-shadow: 0 6px 18px rgba(0,0,0,0.08); overflow: hidden; }
.card-header { background: linear-gradient(90deg, #198754, #28a745); }
.card-header h4 { color: #fff; margin: 0; font-weight: 700; }
.card-body { padding: 2rem; }
.form-label { font-weight: 600; }
.section-title { color:#198754; font-weight:800; margin-top: .25rem; }
hr.soft { border: 0; border-top: 1px solid #e9ecef; margin: 1.25rem 0; }
.form-label::after { content: " *"; color: red; }
</style>

<div class="row justify-content-center mt-4">
  <div class="col-xl-9 col-lg-10">
    <div class="card profile-card">
      <div class="card-header">
        <h4 class="mb-0"><i class="bi bi-pencil-square me-1"></i> Edit Contact & Profile</h4>
      </div>

      <div class="card-body">
        <form method="POST" action="/user/profile_save.php" id="profileForm">
          <input type="hidden" name="action" value="edit_contact">

          <h5 class="section-title">Account Details</h5>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label" for="name">Full Name</label>
              <input type="text" class="form-control form-control-lg" id="name" name="name" value="<?= e($user['name']) ?>" required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="email">Email Address</label>
              <input type="email" class="form-control form-control-lg" id="email" name="email" value="<?= e($user['email']) ?>" required>
            </div>
          </div>

          <hr class="soft">

          <h5 class="section-title">Personal & Contact</h5>
          <div class="row g-3">
            <div class="col-md-12">
              <label class="form-label" for="phone">Phone Number</label>
              <input type="text" class="form-control form-control-lg" id="phone" name="phone" value="<?= e($user['phone']) ?>" placeholder="e.g., 7501234567" required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="gender">Gender</label>
              <select class="form-select form-select-lg" id="gender" name="gender" required>
                <option value="" <?= $selected('', $user['gender']) ?> disabled>Select Gender</option>
                <option value="male" <?= $selected('male', $user['gender']) ?>>Male</option>
                <option value="female" <?= $selected('female', $user['gender']) ?>>Female</option>
                <option value="others" <?= $selected('others', $user['gender']) ?>>Other</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="age">Age</label>
              <input type="number" class="form-control form-control-lg" id="age" name="age" min="16" max="99" value="<?= e($user['age']) ?>" placeholder="Must be 16 or above" required>
            </div>
            <div class="col-12">
              <label class="form-label" for="address">Address Line 1</label>
              <input type="text" class="form-control form-control-lg" id="address" name="address" value="<?= e($user['address']) ?>" placeholder="Street Address" required>
            </div>
            <div class="col-12">
              <label class="form-label" for="address2">Address Line 2</label>
              <input type="text" class="form-control form-control-lg" id="address2" name="address2" value="<?= e($user['address2']) ?>" placeholder="Apartment, suite, etc." required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="city">City</label>
              <input type="text" class="form-control form-control-lg" id="city" name="city" value="<?= e($user['city']) ?>" placeholder="City Name" required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="country">Country</label>
              <select class="form-select form-select-lg" id="country" name="country" required>
                <option value="" disabled <?= empty($user['country']) ? 'selected' : '' ?>>Select Country</option>
                <?php foreach ($countries as $country_name): ?>
                    <option value="<?= e($country_name) ?>" <?= $selected($country_name, $user['country']) ?>>
                        <?= e($country_name) ?>
                    </option>
                <?php endforeach; ?>
              </select>
            </div>
          </div>

          <hr class="soft">

          <h5 class="section-title">Education</h5>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label" for="highest_degree">Highest Degree</label>
              <input type="text" class="form-control" id="highest_degree" name="highest_degree" value="<?= e($user['highest_degree'] ?? '') ?>" placeholder="e.g., MSc in Electrical Engineering" required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="institution">Institution</label>
              <input type="text" class="form-control" id="institution" name="institution" value="<?= e($user['institution'] ?? '') ?>" placeholder="e.g., University of Leicester" required>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="graduation_year">Graduation Year</label>
              <input type="text" class="form-control" id="graduation_year" name="graduation_year" value="<?= e($user['graduation_year'] ?? '') ?>" placeholder="e.g., 2014" required>
            </div>
          </div>

          <hr class="soft">

          <h5 class="section-title">Experience</h5>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label" for="experience_title">Job Title</label>
              <input type="text" class="form-control" id="experience_title" name="experience_title" value="<?= e($user['experience_title'] ?? '') ?>" placeholder="e.g., Electrical Engineer" required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="experience_company">Company</label>
              <input type="text" class="form-control" id="experience_company" name="experience_company" value="<?= e($user['experience_company'] ?? '') ?>" placeholder="e.g., MOF-ENG" required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="experience_years">Years (range)</label>
              <input type="text" class="form-control" id="experience_years" name="experience_years" value="<?= e($user['experience_years'] ?? '') ?>" placeholder="e.g., 2018–2024" required>
            </div>
            <div class="col-12">
              <label class="form-label" for="experience_description">Description</label>
              <textarea class="form-control" id="experience_description" name="experience_description" rows="4" placeholder="Short summary..." required><?= e($user['experience_description'] ?? '') ?></textarea>
            </div>
          </div>

          <hr class="soft">

          <h5 class="section-title">Skills</h5>
          <div class="mb-4">
            <label class="form-label" for="skills">Skills (comma separated)</label>
            <input type="text" class="form-control" id="skills" name="skills" value="<?= e($user['skills'] ?? '') ?>" placeholder="e.g., PHP, AutoCAD, Excel, Safety Audits" required>
          </div>

          <div class="d-grid gap-2">
            <button type="submit" class="btn btn-success btn-lg"><i class="bi bi-save me-1"></i> Save Changes</button>
            <a href="/user/dashboard.php" class="btn btn-outline-secondary">Cancel and Go Back</a>
          </div>
        </form>
      </div>
    </div>
  </div>
</div>

<script>
document.getElementById('profileForm').addEventListener('submit', function(e) {
    const ageInput = document.getElementById('age');
    if (parseInt(ageInput.value) < 16) {
        e.preventDefault();
        alert('You must be at least 16 years old to save your profile.');
        ageInput.focus();
    }
});
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>