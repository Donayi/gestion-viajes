from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_admin_backup_page_and_navigation_contract():
    page = (ROOT / "frontend/src/app/(protected)/admin/respaldos/page.tsx").read_text(encoding="utf-8")
    navigation = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    service = (ROOT / "frontend/src/services/respaldos.service.ts").read_text(encoding="utf-8")
    assert 'title="Respaldos"' in page
    assert "Generar respaldo" in page
    assert "archivos físicos almacenados en R2 no se incluyen" in page
    assert "Descargar" in page
    assert 'href: "/admin/respaldos"' in navigation
    assert '"/respaldos/manual"' in service
    assert '"/respaldos?page=1&page_size=100"' in service
    assert "/descarga`" in service


def test_development_does_not_keep_stale_next_bundles_in_pwa_cache():
    register = (ROOT / "frontend/src/components/pwa/service-worker-register.tsx").read_text(
        encoding="utf-8"
    )
    assert 'process.env.NODE_ENV === "development"' in register
    assert '.getRegistration("/")' in register
    assert ".unregister()" in register
    assert 'cacheName.startsWith("DAFREQ_CACHE_")' in register
    assert 'navigator.serviceWorker.register("/sw.js")' in register
