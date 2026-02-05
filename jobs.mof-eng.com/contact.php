<?php 
$page_title = 'Contact';
include __DIR__ . '/includes/header.php'; 
?>

<style>
  .contact-section {
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem 1rem 4rem 1rem;
  }

  .contact-section h3 {
    color: #198754;
    font-weight: 700;
  }

  .contact-info {
    background: #f8fdf9;
    border-left: 4px solid #198754;
    border-radius: 0.75rem;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }

  .contact-info h5 {
    color: #198754;
    font-weight: 600;
  }

  .contact-info p {
    margin-bottom: 0.4rem;
  }

  .map-container {
    border: 1px solid #e9ecef;
    border-radius: 0.75rem;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  }

  iframe {
    width: 100%;
    height: 350px;
    border: 0;
  }
</style>

<div class="contact-section">
  <h3 class="fw-bold mb-3"><i class="bi bi-envelope-fill me-2"></i>Contact Us</h3>
  <p class="text-muted mb-4">
    We’re always happy to hear from you. You can reach out to us by email, phone, or by visiting our office in Sulaymaniyah.
  </p>

  <!-- 🏢 Contact Information -->
  <div class="contact-info">
    <h5><i class="bi bi-geo-alt-fill me-2"></i>Our Address</h5>
    <p><strong>MANAGING OF FUTURE ENG COMPANY</strong></p>
    <p>New Chwarchra, House No. A1-345</p>
    <p>Near Sara petrol station, Slemani, Iraq</p>
    <p class="mb-2"><i class="bi bi-telephone-fill me-1"></i><strong>Phone:</strong> 00964 770 533 0101</p>
    <p><i class="bi bi-envelope-at-fill me-1"></i><strong>Email:</strong> 
      <a href="mailto:hr@mof-eng.com" class="text-success fw-semibold">hr@mof-eng.com</a>
    </p>
  </div>

  <!-- 🗺️ Embedded Google Map -->
  <div class="map-container">
    <iframe
      src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3084.646347309021!2d45.3998997!3d35.5483641!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x40002f2af22b4343%3A0x7d186ed832f76fd2!2sManaging%20Of%20Future%20Eng%20Company!5e0!3m2!1sen!2siq!4v1730000000000!5m2!1sen!2siq"
      allowfullscreen=""
      loading="lazy"
      referrerpolicy="no-referrer-when-downgrade">
    </iframe>
  </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>
