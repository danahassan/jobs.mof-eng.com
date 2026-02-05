<?php
header('Content-Type: application/json');
require __DIR__ . '/../db.php';

ini_set('display_errors', 1);
error_reporting(E_ALL);

$draw   = (int)($_GET['draw'] ?? 1);
$start  = (int)($_GET['start'] ?? 0);
$length = (int)($_GET['length'] ?? 10);
$search = trim($_GET['search']['value'] ?? '');
$position = $_GET['position'] ?? '';
$status   = $_GET['status'] ?? '';
$source   = $_GET['source'] ?? '';
$dateFrom = $_GET['dateFrom'] ?? '';
$dateTo   = $_GET['dateTo'] ?? '';

$where = [];
$params = [];
$types = '';

// 🔍 Search
if ($search !== '') {
    if (is_numeric($search)) {
        $where[] = "(id=? OR firstname LIKE CONCAT('%',?,'%') OR lastname LIKE CONCAT('%',?,'%') OR email LIKE CONCAT('%',?,'%'))";
        $params = array_merge($params, [$search,$search,$search,$search]);
        $types .= 'isss';
    } else {
        $where[] = "(firstname LIKE CONCAT('%',?,'%') OR lastname LIKE CONCAT('%',?,'%') OR email LIKE CONCAT('%',?,'%'))";
        $params = array_merge($params, [$search,$search,$search]);
        $types .= 'sss';
    }
}

// 🎯 Filters
if ($position !== '') { $where[]="position=?"; $params[]=$position; $types.='s'; }
if ($status   !== '') { $where[]="status=?";   $params[]=$status;   $types.='s'; }
if ($source   !== '') { $where[]="source=?";   $params[]=$source;   $types.='s'; }
if ($dateFrom !== '') { $where[]="DATE(applied_at)>=?"; $params[]=$dateFrom; $types.='s'; }
if ($dateTo   !== '') { $where[]="DATE(applied_at)<=?"; $params[]=$dateTo;   $types.='s'; }

$whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

// 📊 Counts
$total = $conn->query("SELECT COUNT(*) c FROM job_applications")->fetch_assoc()['c'] ?? 0;

// Filtered count
$stmt = $conn->prepare("SELECT COUNT(*) c FROM job_applications $whereSql");
if ($types) $stmt->bind_param($types, ...$params);
$stmt->execute();
$stmt->bind_result($filtered);
$stmt->fetch();
$stmt->close();

// 🧾 Data
$orderColIndex = (int)($_GET['order'][0]['column'] ?? 0);
$orderDir = ($_GET['order'][0]['dir'] ?? 'desc') === 'asc' ? 'ASC' : 'DESC';
$cols = ['applied_at','CONCAT(firstname," ",lastname)','email','phone','position','status','source','age','gender','resume_path'];
$orderBy = $cols[$orderColIndex] ?? 'applied_at';

$query = "SELECT applied_at, CONCAT(firstname,' ',lastname) AS name, email, phone, position, status, source, age, gender, resume_path
          FROM job_applications $whereSql
          ORDER BY $orderBy $orderDir
          LIMIT ?,?";
$params_data = array_merge($params, [$start,$length]);
$types_data = $types . 'ii';
$stmt = $conn->prepare($query);
$stmt->bind_param($types_data, ...$params_data);
$stmt->execute();

// ✅ Use bind_result instead of get_result()
$stmt->bind_result($applied_at, $name, $email, $phone, $position, $status, $source, $age, $gender, $resume_path);

$data = [];
$colors = [
  'Hired'=>'success','Interview'=>'info','Offer'=>'primary',
  'Screening'=>'warning','Rejected'=>'danger','New'=>'secondary'
];
while ($stmt->fetch()) {
  $badge = '<span class="badge text-bg-'.($colors[$status]??'secondary').'">'.htmlspecialchars($status).'</span>';
  $cv = $resume_path
      ? '<a href="'.htmlspecialchars($resume_path).'" target="_blank" class="btn btn-sm btn-outline-success"><i class="bi bi-file-earmark-arrow-down"></i> CV</a>'
      : '-';
  $data[] = [
    (new DateTime($applied_at))->format('Y-m-d H:i'),
    htmlspecialchars($name),
    htmlspecialchars($email),
    htmlspecialchars($phone),
    htmlspecialchars($position ?? 'N/A'),
    $badge,
    htmlspecialchars($source),
    (int)$age,
    htmlspecialchars($gender),
    $cv
  ];
}
$stmt->close();

echo json_encode([
  'draw' => $draw,
  'recordsTotal' => $total,
  'recordsFiltered' => $filtered,
  'data' => $data
]);
exit;
?>
