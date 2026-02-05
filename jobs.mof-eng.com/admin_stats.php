<?php
header('Content-Type: application/json');
require __DIR__ . '/db.php';

$labelsS = []; $valuesS = [];
$res = $conn->query("SELECT status, COUNT(*) c FROM job_applications GROUP BY status ORDER BY c DESC");
while($r=$res->fetch_assoc()){ $labelsS[] = $r['status'] ?: 'Unknown'; $valuesS[] = (int)$r['c']; }

$labelsSrc=[]; $valuesSrc=[];
$res2 = $conn->query("SELECT source, COUNT(*) c FROM job_applications GROUP BY source ORDER BY c DESC");
while($r=$res2->fetch_assoc()){ $labelsSrc[] = $r['source'] ?: 'Unknown'; $valuesSrc[] = (int)$r['c']; }

echo json_encode([
  'by_status'=>['labels'=>$labelsS,'values'=>$valuesS],
  'by_source'=>['labels'=>$labelsSrc,'values'=>$valuesSrc],
  'kpi'=>[
    'total'=>(int)$conn->query("SELECT COUNT(*) c FROM job_applications")->fetch_assoc()['c'],
    'last7d'=>(int)$conn->query("SELECT COUNT(*) c FROM job_applications WHERE applied_at >= (NOW() - INTERVAL 7 DAY)")->fetch_assoc()['c'],
    'interview'=>(int)$conn->query("SELECT COUNT(*) c FROM job_applications WHERE status='Interview'")->fetch_assoc()['c'],
    'hired'=>(int)$conn->query("SELECT COUNT(*) c FROM job_applications WHERE status='Hired'")->fetch_assoc()['c']
  ]
]);
