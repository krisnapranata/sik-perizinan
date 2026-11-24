/* Peta Pusat Informasi Investasi.
   Mode "js" (ada GOOGLE_MAPS_API_KEY): semua titik di satu peta Google Maps.
   Mode "embed" (tanpa kunci): iframe Google Maps, satu titik; tombol "Lihat di peta" memindahkannya. */
(function () {
  var el = document.getElementById("peta");
  if (!el) return;
  var titik = JSON.parse(document.getElementById("data-titik").textContent);
  var pusat = JSON.parse(document.getElementById("data-pusat").textContent);
  var keterangan = document.getElementById("keterangan-peta");
  var tampilkan = function () {};

  function cari(id) {
    for (var i = 0; i < titik.length; i++) if (titik[i].id === id) return titik[i];
    return null;
  }

  /* Isi jendela info dibangun lewat DOM (textContent) agar nama dari admin tidak dieksekusi sebagai HTML. */
  function isiInfo(t) {
    var d = document.createElement("div"), b = document.createElement("b"),
        s = document.createElement("div"), a = document.createElement("a");
    d.className = "peta-info";
    b.textContent = t.nama;
    s.textContent = t.tingkat + " · " + t.sektor + " · Kec. " + t.kecamatan;
    a.href = t.url;
    a.textContent = "Lihat profil";
    d.appendChild(b); d.appendChild(s); d.appendChild(a);
    return d;
  }

  if (el.dataset.mode === "js") {
    window.sikPetaSiap = function () {
      var peta = new google.maps.Map(el, {
        center: pusat, zoom: 11, mapTypeControl: false, streetViewControl: false, fullscreenControl: true
      });
      var info = new google.maps.InfoWindow(), batas = new google.maps.LatLngBounds(), penanda = {};
      titik.forEach(function (t) {
        var m = new google.maps.Marker({ position: { lat: t.lat, lng: t.lng }, map: peta, title: t.nama });
        batas.extend(m.getPosition());
        m.addListener("click", function () { info.setContent(isiInfo(t)); info.open({ anchor: m, map: peta }); });
        penanda[t.id] = m;
      });
      if (titik.length > 1) peta.fitBounds(batas, 48);
      tampilkan = function (t) {
        var m = penanda[t.id];
        peta.panTo(m.getPosition());
        peta.setZoom(14);
        info.setContent(isiInfo(t));
        info.open({ anchor: m, map: peta });
      };
    };
  } else {
    var frame = document.getElementById("peta-embed");
    tampilkan = function (t) {
      frame.src = "https://maps.google.com/maps?q=" + t.lat + "," + t.lng + "&z=14&hl=id&output=embed";
      frame.title = "Peta lokasi " + t.nama;
      if (keterangan) keterangan.textContent = "Menampilkan " + t.nama + ".";
    };
  }

  document.addEventListener("click", function (e) {
    var tombol = e.target.closest("[data-tampil-peta]");
    if (!tombol) return;
    var t = cari(Number(tombol.dataset.tampilPeta));
    if (!t) return;
    tampilkan(t);
    el.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
})();
