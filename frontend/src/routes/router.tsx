// Router por rol (Requirement 8). Estructura:
//  /                     → encamina según rol activo
//  /seleccionar-rol      → selección de rol (sin rol activo)
//  /educadora/*          → secciones de educadora (GuardRol)
//  /directora/*          → sección de directora (GuardRol)
//
// Se usa HashRouter para funcionar sin configuración de servidor en la demo /
// despliegue estático de la PWA.

import { createHashRouter, Navigate } from "react-router-dom";
import { AppLayout } from "../layout/AppLayout";
import { GuardRol } from "./GuardRol";
import { Inicio } from "./Inicio";
import { SeleccionarRol } from "../screens/SeleccionarRol";
import { MiSala } from "../screens/educadora/MiSala";
import { Capturar } from "../screens/educadora/Capturar";
import { ConfirmarClasificacion } from "../screens/educadora/ConfirmarClasificacion";
import { FichaNino } from "../screens/educadora/FichaNino";
import { Bitacoras } from "../screens/educadora/Bitacoras";
import { DashboardDireccion } from "../screens/directora/DashboardDireccion";

export const router = createHashRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <Inicio /> },
      { path: "seleccionar-rol", element: <SeleccionarRol /> },

      {
        path: "educadora",
        element: <GuardRol rolRequerido="educadora" />,
        children: [
          { index: true, element: <Navigate to="mi-sala" replace /> },
          { path: "mi-sala", element: <MiSala /> },
          { path: "capturar", element: <Capturar /> },
          { path: "observaciones/:idObservacion/clasificacion", element: <ConfirmarClasificacion /> },
          { path: "ninos/:idNino", element: <FichaNino /> },
          { path: "bitacoras", element: <Bitacoras /> },
        ],
      },

      {
        path: "directora",
        element: <GuardRol rolRequerido="directora" />,
        children: [
          { index: true, element: <Navigate to="dashboard" replace /> },
          { path: "dashboard", element: <DashboardDireccion /> },
        ],
      },

      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
