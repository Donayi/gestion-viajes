import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  BellRing,
  Box,
  Building2,
  ClipboardPlus,
  FileText,
  Home,
  IdCard,
  KeyRound,
  ListChecks,
  Map,
  MessageSquareShare,
  PlusCircle,
  Settings2,
  Truck,
  UserCog,
  Users
} from "lucide-react";

export type NavigationItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export type NavigationSection = {
  title: string;
  items: NavigationItem[];
};

export const adminNavigationSections: NavigationSection[] = [
  {
    title: "Dashboard",
    items: [
      { href: "/dashboard", label: "Inicio", icon: Home },
      { href: "/dashboard/kpis", label: "KPIs operativos", icon: BarChart3 }
    ]
  },
  {
    title: "Operación",
    items: [
      { href: "/viajes", label: "Viajes", icon: Truck },
      { href: "/admin/mapa-viajes", label: "Mapa de viajes", icon: Map },
      { href: "/admin/viajes/nuevo", label: "Crear viaje", icon: ClipboardPlus },
      { href: "/admin/disponibilidad", label: "Disponibilidad", icon: Settings2 },
      { href: "/admin/mantenimientos", label: "Mantenimientos", icon: Settings2 },
      { href: "/admin/alertas", label: "Alertas", icon: BellRing },
      { href: "/admin/telegram", label: "Telegram / Notificaciones", icon: MessageSquareShare }
    ]
  },
  {
    title: "Administración",
    items: [
      { href: "/admin/roles", label: "Roles", icon: KeyRound },
      { href: "/admin/usuarios", label: "Usuarios", icon: Users },
      { href: "/admin/operadores", label: "Operadores", icon: IdCard },
      { href: "/admin/clientes", label: "Clientes", icon: Building2 },
      { href: "/admin/trailers", label: "Tráilers", icon: Truck },
      { href: "/admin/cajas", label: "Cajas", icon: Box }
    ]
  },
  {
    title: "Documentación",
    items: [
      { href: "/admin/documentos", label: "Documentos", icon: FileText }
    ]
  },
  {
    title: "Sistema",
    items: [{ href: "/admin/perfil", label: "Perfil", icon: UserCog }]
  }
];

export const operatorNavigationItems: NavigationItem[] = [
  { href: "/dashboard", label: "Inicio", icon: Home },
  { href: "/viajes", label: "Mis viajes", icon: Truck },
  { href: "/dashboard/kpis", label: "KPIs", icon: BarChart3 }
];

export const maintenanceNavigationItems: NavigationItem[] = [
  { href: "/mantenimiento", label: "Mantenimientos", icon: ListChecks },
  { href: "/mantenimiento/nuevo", label: "Nueva orden", icon: PlusCircle },
];
