<?php
// /admin/registered_users.php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';
$page_title = "Registered Users";
include __DIR__ . '/../includes/header.php';

// Country list for the modal dropdown
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

$result = $conn->query("SELECT * FROM users WHERE role='user' ORDER BY created_at DESC");
?>

<div class="container my-5">
  <div class="card shadow-sm border-0">
    <div class="card-header bg-white border-0 d-flex justify-content-between align-items-center">
      <h4 class="fw-bold text-success mb-0"><i class="bi bi-people-fill me-2"></i>Registered Users</h4>
      <button class="btn btn-outline-success btn-sm" onclick="location.reload()">
        <i class="bi bi-arrow-clockwise"></i> Refresh
      </button>
    </div>

    <div class="card-body">
      <div class="table-responsive">
        <table id="usersTable" class="table table-hover align-middle">
          <thead class="table-success text-center">
            <tr>
              <th>#</th>
              <th>Photo</th>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>City</th>
              <th>Country</th>
              <th>Registered</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <?php 
            $i=1;
            while($u = $result->fetch_assoc()): 
              $photo = $u['profile_photo_path'] ?: ($u['gender']=='female' ? '/uploads/profiles/default_female.png' : '/uploads/profiles/default_male.png');
            ?>
            <tr>
              <td class="text-center"><?= $i++ ?></td>
              <td class="text-center">
                <img src="<?= htmlspecialchars($photo) ?>" width="40" height="40" class="rounded-circle shadow-sm" style="object-fit:cover;">
              </td>
              <td class="fw-bold"><?= htmlspecialchars($u['name']) ?></td>
              <td><?= htmlspecialchars($u['email']) ?></td>
              <td><?= htmlspecialchars($u['phone']) ?></td>
              <td><?= htmlspecialchars($u['city'] ?? '—') ?></td>
              <td><?= htmlspecialchars($u['country'] ?? '—') ?></td>
              <td class="text-center"><?= date('M d, Y', strtotime($u['created_at'])) ?></td>
              <td class="text-center">
                <div class="btn-group" role="group">
                  <a href="/admin/user_view.php?id=<?= $u['id'] ?>" class="btn btn-sm btn-outline-success" title="View Full Profile">
                    <i class="bi bi-eye"></i>
                  </a>
                  
                  <button class="btn btn-sm btn-outline-primary" 
                          onclick="openEditModal(<?= $u['id'] ?>, '<?= htmlspecialchars(addslashes($u['name'])) ?>', '<?= htmlspecialchars(addslashes($u['email'])) ?>', '<?= htmlspecialchars(addslashes($u['phone'])) ?>', '<?= htmlspecialchars(addslashes($u['city'])) ?>', '<?= htmlspecialchars(addslashes($u['country'])) ?>')"
                          title="Quick Edit">
                    <i class="bi bi-pencil-square"></i>
                  </button>

                  <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(<?= $u['id'] ?>)" title="Delete User">
                    <i class="bi bi-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
            <?php endwhile; ?>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="editUserModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="editUserForm" method="post" action="/admin/user_edit_save.php">
        <div class="modal-header bg-success text-white">
          <h5 class="modal-title"><i class="bi bi-pencil-square me-2"></i>Edit User Info</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <input type="hidden" name="id" id="edit_id">
          <div class="mb-3">
            <label class="form-label fw-bold">Full Name</label>
            <input type="text" name="name" id="edit_name" class="form-control" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Email Address</label>
            <input type="email" name="email" id="edit_email" class="form-control" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Phone Number</label>
            <input type="text" name="phone" id="edit_phone" class="form-control">
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">City</label>
            <input type="text" name="city" id="edit_city" class="form-control">
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Country</label>
            <select name="country" id="edit_country" class="form-select">
              <option value="">Select Country</option>
              <?php foreach($countries as $c): ?>
                <option value="<?= $c ?>"><?= $c ?></option>
              <?php endforeach; ?>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button type="submit" class="btn btn-success px-4 fw-bold">Save Changes</button>
          <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancel</button>
        </div>
      </form>
    </div>
  </div>
</div>

<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">

<script>
$(document).ready(() => {
  $('#usersTable').DataTable({
    pageLength: 10,
    order: [[0,'asc']],
    language: { 
      search: "_INPUT_", 
      searchPlaceholder: "Quick search users..." 
    }
  });
});

function openEditModal(id, name, email, phone, city, country) {
  $('#edit_id').val(id);
  $('#edit_name').val(name);
  $('#edit_email').val(email);
  $('#edit_phone').val(phone);
  $('#edit_city').val(city);
  $('#edit_country').val(country);
  new bootstrap.Modal(document.getElementById('editUserModal')).show();
}

function deleteUser(id) {
  if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;
  $.post('/admin/user_delete.php', { id }, (res) => {
      // Assuming success, reload
      location.reload();
  }).fail(() => {
      alert('Error deleting user. They may have linked applications.');
  });
}
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>