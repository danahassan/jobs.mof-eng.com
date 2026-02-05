<?php 
$page_title = 'About';
include __DIR__ . '/includes/header.php'; 
?>

<style>
  .about-section {
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem 1rem 4rem 1rem;
  }

  .about-section h3 {
    color: #198754;
    font-weight: 700;
  }

  .highlight-box {
    background: #f8fdf9;
    border-left: 4px solid #198754;
    padding: 1rem 1.25rem;
    border-radius: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .highlight-box h5 {
    font-weight: 600;
    color: #198754;
  }

  .values-list li {
    margin-bottom: 0.6rem;
  }

  .facts {
    background-color: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 0.75rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    padding: 2rem;
    text-align: center;
  }

  .fact-number {
    font-size: 2rem;
    font-weight: 700;
    color: #198754;
  }

  .fact-label {
    color: #6c757d;
  }

  .mission-vision {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
  }

  .mission-vision .card {
    flex: 1;
    min-width: 250px;
    border: none;
    border-radius: 0.75rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  }

  .mission-vision .card-title {
    color: #198754;
    font-weight: 600;
  }

  .mission-vision .card-body {
    background-color: #fdfefc;
  }
</style>

<div class="about-section">

  <h3 class="fw-bold mb-3"><i class="bi bi-building-check me-2"></i>About Managing Of Future Engineering Company (MOF-ENG)</h3>

  <p class="text-muted mb-4">
    <strong>Managing Of Future Engineering Company (MOF-ENG)</strong> is a growing engineering and construction service company based in Sulaymaniyah, Iraq.  
    We are dedicated to delivering reliable, safe, and efficient solutions with a focus on quality and sustainability.
  </p>

  <div class="highlight-box">
    <h5><i class="bi bi-lightbulb me-2"></i>Who We Are</h5>
    <p class="mb-0">
      MOF-ENG is built on a foundation of trust, professionalism, and teamwork.  
      Our experienced staff and engineers have successfully executed a wide range of industrial and infrastructure projects across the region.  
      We take pride in our consistency, strong work ethics, and long-term client partnerships.
    </p>
  </div>

  <div class="mission-vision mb-4">
    <div class="card">
      <div class="card-body">
        <h5 class="card-title"><i class="bi bi-bullseye me-2"></i>Our Vision</h5>
        <p class="card-text text-muted mb-0">
          To grow as a trusted local company recognized for quality, integrity, and innovation in every project we deliver.
        </p>
      </div>
    </div>

    <div class="card">
      <div class="card-body">
        <h5 class="card-title"><i class="bi bi-rocket-takeoff me-2"></i>Our Mission</h5>
        <p class="card-text text-muted mb-0">
          To provide reliable and cost-effective engineering solutions while maintaining the highest standards of safety, quality, and client satisfaction.
        </p>
      </div>
    </div>
  </div>

  <div class="highlight-box">
    <h5><i class="bi bi-gem me-2"></i>Our Core Values</h5>
    <ul class="values-list text-muted">
      <li><strong>Integrity:</strong> We act with honesty and responsibility in all aspects of our work.</li>
      <li><strong>Quality:</strong> We aim to exceed expectations through careful planning and execution.</li>
      <li><strong>Safety:</strong> We ensure a safe and healthy environment for our team and partners.</li>
      <li><strong>Commitment:</strong> We value reliability and long-term relationships with our clients.</li>
      <li><strong>Teamwork:</strong> We believe that collaboration is key to success.</li>
    </ul>
  </div>

  <div class="row g-4 my-4">
    <div class="col-md-4">
      <div class="facts">
        <div class="fact-number"><i class="bi bi-people-fill me-2"></i>50-100</div>
        <div class="fact-label">Employees & Engineers</div>
      </div>
    </div>
    <div class="col-md-4">
      <div class="facts">
        <div class="fact-number"><i class="bi bi-geo-alt-fill me-2"></i>1</div>
        <div class="fact-label">Main Location — Sulaymaniyah</div>
      </div>
    </div>
    <div class="col-md-4">
      <div class="facts">
        <div class="fact-number"><i class="bi bi-check2-circle me-2"></i>100+</div>
        <div class="fact-label">Completed Projects</div>
      </div>
    </div>
  </div>

  <div class="highlight-box mb-5">
    <h5><i class="bi bi-briefcase-fill me-2"></i>About MOF-ENG Careers Portal</h5>
    <p class="text-muted mb-0">
      The <strong>MOF-ENG Careers Portal</strong> connects talented professionals with job opportunities at our company.  
      Applicants can explore openings, apply directly, and track their application status with ease.  
      We are committed to building a team that shares our values and contributes to our mission of excellence and innovation.
    </p>
  </div>

  <p class="text-center text-muted small">
    <i class="bi bi-envelope-at"></i> For more information, contact us at  
    <a href="mailto:info@mof-eng.com" class="text-success fw-semibold">info@mof-eng.com</a>
  </p>

</div>

<?php include __DIR__ . '/includes/footer.php'; ?>
