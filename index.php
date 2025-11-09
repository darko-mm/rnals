<!DOCTYPE html>
<html lang="hr">
<head>
  <meta charset="UTF-8">
  <title>Prikaz broja</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light text-center mt-5">

  <h5 id="title" style="font-size: 20px; width: 100vw;" class="text-primary text-center mt-5">Zadnji broj radnog naloga:</h5>
  <div id="broj" style="font-size: 80px; font-weight: bold; width: 100vw;" class="text-primary text-center mt-5">
</div>

<div id="details-container" class="container mt-5"></div>

  <script>
    function ucitajBroj() {
      fetch("data.txt?" + new Date().getTime())
        .then(response => response.text())
        .then(data => {
          document.getElementById("broj").innerText = data.trim();
        });
    }

    function ucitajDetalje() {
      fetch("work_order_details.html?" + new Date().getTime())
        .then(response => response.text())
        .then(data => {
          document.getElementById("details-container").innerHTML = data;
        });
    }

    ucitajBroj();
    ucitajDetalje();
  </script>

</body>
</html>
