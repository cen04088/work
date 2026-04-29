// 카카오맵 지도 초기화
function initMap(containerId, lat = 37.5665, lon = 126.9780, level = 6) {
  const container = document.getElementById(containerId);
  if (!container) return null;
  const options = { center: new kakao.maps.LatLng(lat, lon), level };
  return new kakao.maps.Map(container, options);
}

// 마커 + 인포윈도우 생성
function addMarker(map, lat, lon, name, phone) {
  const marker = new kakao.maps.Marker({
    map,
    position: new kakao.maps.LatLng(lat, lon),
  });
  
  const phoneHtml = phone ? `<a href="tel:${phone}" style="color:#1A73E8">${phone}</a>` : '<span style="color:#999">전화번호 없음</span>';
  
  const infoContent = `
    <div style="padding:12px;min-width:180px;font-size:15px;color:#333;">
      <strong>${name}</strong><br>
      ${phoneHtml}
    </div>
  `;
  const infowindow = new kakao.maps.InfoWindow({ content: infoContent });
  kakao.maps.event.addListener(marker, 'click', () => {
    infowindow.open(map, marker);
  });
  return { marker, infowindow };
}

// GPS 현재 위치 요청
function getCurrentLocation(successCb, errorCb) {
  if (!navigator.geolocation) {
    if(errorCb) errorCb("위치 서비스를 지원하지 않는 기기입니다.");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    pos => successCb(pos.coords.latitude, pos.coords.longitude),
    () => {
      if(errorCb) errorCb("위치 정보를 가져오지 못했습니다. 직접 지역을 선택해주세요.");
    }
  );
}
