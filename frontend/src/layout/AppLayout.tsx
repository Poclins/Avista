// AppLayout — estructura común a todas las pantallas. Mantiene visible y
// persistente el BannerDatosSinteticos (Requirement 9.4), el SelectorRol
// (Requirement 8.4) y la navegación por rol. Renderiza la ruta activa vía
// <Outlet>.

import { NavLink, Outlet } from "react-router-dom";
import { BannerDatosSinteticos } from "../components/BannerDatosSinteticos";
import { SelectorRol } from "../components/SelectorRol";
import { useRol } from "../roles/RolContext";
import { NAV_EDUCADORA, NAV_DIRECTORA } from "../routes/navegacion";

export function AppLayout() {
  const { rol } = useRol();
  const items =
    rol === "educadora" ? NAV_EDUCADORA : rol === "directora" ? NAV_DIRECTORA : [];

  return (
    <div className="app-shell">
      <BannerDatosSinteticos />

      <header className="app-header">
        <div className="app-header__marca">
          <strong>jAImes</strong>
          <span className="app-header__sub">Fundación Integra</span>
        </div>
        <SelectorRol />
      </header>

      {items.length > 0 ? (
        <nav className="app-nav" aria-label="Navegación principal">
          {items.map((item) => (
            <NavLink
              key={item.ruta}
              to={item.ruta}
              className={({ isActive }) =>
                `touch-target nav-link${isActive ? " nav-link--activo" : ""}`
              }
            >
              {item.etiqueta}
            </NavLink>
          ))}
        </nav>
      ) : null}

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
