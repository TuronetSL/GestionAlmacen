const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT = '/home/user/GestionBiblioteca/screens';
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT);

// ─── Shared layout pieces ───────────────────────────────────────────────────
const CSS = `
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',system-ui,sans-serif; background:#0f1117; color:#e2e8f0; display:flex; height:100vh; overflow:hidden; }
.sidebar { width:220px; min-width:220px; background:linear-gradient(180deg,#131720,#0f1117); border-right:1px solid rgba(255,255,255,.055); display:flex; flex-direction:column; box-shadow:4px 0 24px rgba(0,0,0,.5); }
.s-logo { padding:14px 14px 11px; border-bottom:1px solid rgba(255,255,255,.05); display:flex; align-items:center; gap:9px; }
.s-logo-icon { width:32px; height:32px; border-radius:9px; background:linear-gradient(135deg,#06b6d4,#0284c7); display:flex; align-items:center; justify-content:center; font-size:15px; flex-shrink:0; }
.s-logo-name { font-size:12px; font-weight:700; color:#fff; }
.s-logo-sub { font-size:9px; color:#4b5563; letter-spacing:.8px; text-transform:uppercase; }
.s-nav { flex:1; overflow-y:auto; padding:6px 0; }
.s-nav::-webkit-scrollbar { width:2px; } .s-nav::-webkit-scrollbar-thumb { background:rgba(255,255,255,.07); }
.s-dept { margin:0 6px 1px; padding:6px 8px; border-radius:7px; display:flex; align-items:center; gap:7px; cursor:pointer; }
.s-dept:hover { background:rgba(255,255,255,.04); }
.s-dept.it { border:1px solid rgba(99,102,241,.25); background:rgba(99,102,241,.07); }
.s-dept-icon { width:22px; height:22px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:11px; flex-shrink:0; }
.s-dept-name { font-size:11px; font-weight:600; color:#6b7280; }
.s-dept.it .s-dept-name { color:#a5b4fc; }
.it-track { border-left:1px solid rgba(99,102,241,.2); margin-left:19px; margin-right:6px; padding-bottom:2px; }
.it-item { display:flex; align-items:center; gap:7px; padding:5.5px 8px 5.5px 10px; border-radius:6px; font-size:11px; color:#6b7280; cursor:pointer; margin:1px 0; }
.it-item:hover { color:#d1d5db; background:rgba(255,255,255,.04); }
.it-item.active { color:#a5b4fc; background:rgba(99,102,241,.14); font-weight:600; }
.it-item.active::before { content:''; position:absolute; }
.it-sep { font-size:8.5px; font-weight:600; color:#374151; letter-spacing:1px; text-transform:uppercase; padding:7px 8px 3px 10px; }
.s-footer { padding:7px 8px 9px; border-top:1px solid rgba(255,255,255,.05); }
.s-user { display:flex; align-items:center; gap:7px; padding:6px 8px; border-radius:7px; background:rgba(99,102,241,.08); border:1px solid rgba(99,102,241,.2); }
.s-avatar { width:26px; height:26px; border-radius:50%; background:linear-gradient(135deg,#6366f1,#8b5cf6); display:flex; align-items:center; justify-content:center; font-size:9px; font-weight:700; color:#fff; flex-shrink:0; }
.s-uname { font-size:10.5px; font-weight:600; color:#a5b4fc; }
.s-urole { font-size:9px; color:#4b5563; }
.s-dot { width:6px; height:6px; border-radius:50%; background:#10b981; border:2px solid #131720; margin-left:auto; flex-shrink:0; }
.main { flex:1; display:flex; flex-direction:column; overflow:hidden; }
.topbar { height:48px; background:rgba(19,23,32,.95); border-bottom:1px solid rgba(255,255,255,.05); display:flex; align-items:center; padding:0 20px; gap:10px; flex-shrink:0; }
.tb-title { font-size:15px; font-weight:700; color:#fff; flex:1; }
.tb-bc { font-size:11px; color:#4b5563; } .tb-bc span { color:#a5b4fc; }
.tb-btn { padding:6px 12px; border-radius:7px; border:none; font-size:11.5px; font-weight:600; cursor:pointer; }
.btn-pri { background:linear-gradient(135deg,#6366f1,#8b5cf6); color:#fff; }
.btn-sec { background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.08); color:#9ca3af; }
.content { flex:1; overflow-y:auto; padding:18px 20px; }
.page-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
.page-title { font-size:14px; font-weight:700; color:#e2e8f0; }
.page-sub { font-size:11px; color:#4b5563; margin-top:2px; }
.card { background:linear-gradient(135deg,#1a1f2e,#1e2436); border:1px solid rgba(255,255,255,.05); border-radius:11px; padding:14px; }
.card-title { font-size:12px; font-weight:700; color:#e2e8f0; margin-bottom:12px; display:flex; align-items:center; gap:6px; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; }
.grid4 { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.kpi { border-radius:10px; padding:13px 12px; border:1px solid rgba(255,255,255,.05); background:linear-gradient(135deg,#1a1f2e,#1e2436); position:relative; overflow:hidden; }
.kpi-l { font-size:10px; color:#6b7280; margin-bottom:4px; }
.kpi-v { font-size:20px; font-weight:800; color:#fff; margin-bottom:5px; line-height:1; }
.kpi-s { font-size:10px; color:#374151; }
.kpi-i { position:absolute; top:10px; right:10px; width:28px; height:28px; border-radius:7px; display:flex; align-items:center; justify-content:center; font-size:14px; }
table.t { width:100%; border-collapse:collapse; }
table.t th { font-size:10px; font-weight:600; color:#374151; text-transform:uppercase; letter-spacing:.6px; padding:0 8px 8px; text-align:left; }
table.t td { font-size:11.5px; color:#9ca3af; padding:8px 8px; border-top:1px solid rgba(255,255,255,.04); }
table.t td.emp { color:#d1d5db; font-weight:500; }
.badge { display:inline-block; padding:2px 7px; border-radius:20px; font-size:10px; font-weight:600; }
.ok { background:rgba(16,185,129,.14); color:#10b981; }
.warn { background:rgba(245,158,11,.14); color:#f59e0b; }
.err { background:rgba(239,68,68,.14); color:#ef4444; }
.inf { background:rgba(6,182,212,.14); color:#67e8f9; }
.pur { background:rgba(99,102,241,.14); color:#a5b4fc; }
.row { display:flex; align-items:center; gap:10px; padding:9px 12px; border-radius:8px; background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.05); margin-bottom:7px; }
.row:last-child { margin-bottom:0; }
.row-icon { font-size:16px; width:20px; text-align:center; flex-shrink:0; }
.row-info { flex:1; }
.row-name { font-size:12px; font-weight:600; color:#d1d5db; }
.row-sub { font-size:10.5px; color:#4b5563; margin-top:1px; }
.row-right { margin-left:auto; display:flex; align-items:center; gap:6px; flex-shrink:0; }
.search { display:flex; align-items:center; gap:7px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.07); border-radius:7px; padding:5px 10px; }
.search input { background:none; border:none; outline:none; color:#e2e8f0; font-size:11.5px; width:160px; }
.search input::placeholder { color:#374151; }
.filters { display:flex; gap:7px; }
.filter-btn { padding:5px 10px; border-radius:6px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.07); color:#9ca3af; font-size:11px; cursor:pointer; }
.filter-btn.active { background:rgba(99,102,241,.14); border-color:rgba(99,102,241,.3); color:#a5b4fc; }
.prog-bar { height:6px; background:rgba(255,255,255,.06); border-radius:10px; overflow:hidden; margin-top:5px; }
.prog-fill { height:100%; border-radius:10px; }
.sep { height:1px; background:rgba(255,255,255,.05); margin:12px 0; }
input[type=text], input[type=email], input[type=number], select { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:7px; padding:7px 10px; color:#e2e8f0; font-size:12px; width:100%; outline:none; }
label { font-size:11px; color:#6b7280; display:block; margin-bottom:4px; }
.form-group { margin-bottom:12px; }
.form-row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.toggle { width:36px; height:20px; border-radius:20px; position:relative; cursor:pointer; flex-shrink:0; }
.toggle.on { background:linear-gradient(135deg,#6366f1,#8b5cf6); }
.toggle.off { background:rgba(255,255,255,.1); }
.toggle::after { content:''; position:absolute; top:3px; width:14px; height:14px; border-radius:50%; background:#fff; transition:.2s; }
.toggle.on::after { left:19px; }
.toggle.off::after { left:3px; }
.check { width:15px; height:15px; border-radius:4px; display:inline-flex; align-items:center; justify-content:center; font-size:9px; flex-shrink:0; }
.chk-on { background:rgba(99,102,241,.8); color:#fff; }
.chk-off { background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.1); color:transparent; }
.status-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.sd-on { background:#10b981; box-shadow:0 0 6px rgba(16,185,129,.6); }
.sd-off { background:#374151; }
.sd-warn { background:#f59e0b; }
.sd-err { background:#ef4444; }
`;

function sidebar(activeItem) {
  const items = [
    ['Usuarios del sistema','👤'],['Roles y perfiles','🎭'],['Permisos por dpto.','🔑'],['Control accesos AD/LDAP','🔐'],
    ['Configuración general','⚙️'],['Monitor del sistema','📊'],['Logs de actividad','📜'],['Auditoría de cambios','🕵️'],
    ['Copias de seguridad','💾'],['Base de datos','🗄️'],['Dispositivos y terminales','📱'],['Integraciones / API','🔗']
  ];
  const depts = [
    ['🏭','Almacén & Logística'],['⚗️','Producción'],['🛒','Compras'],
    ['📦','Ventas'],['🔬','Calidad'],['👥','RRHH'],['🔧','Mantenimiento'],['📊','Dirección']
  ].map(([ic,n])=>`<div class="s-dept"><div class="s-dept-icon" style="background:rgba(255,255,255,.05)">${ic}</div><div class="s-dept-name">${n}</div></div>`).join('');

  const itItems = `
    <div class="it-sep">Usuarios</div>
    ${items.slice(0,4).map(([n,i])=>`<div class="it-item${activeItem===n?' active':''}">${i} ${n}</div>`).join('')}
    <div class="it-sep">Sistema & Datos</div>
    ${items.slice(4,8).map(([n,i])=>`<div class="it-item${activeItem===n?' active':''}">${i} ${n}</div>`).join('')}
    <div class="it-sep">Infraestructura</div>
    ${items.slice(8).map(([n,i])=>`<div class="it-item${activeItem===n?' active':''}">${i} ${n}</div>`).join('')}
  `;

  return `
    <aside class="sidebar">
      <div class="s-logo">
        <div class="s-logo-icon">🧪</div>
        <div><div class="s-logo-name">GestorAlmacén Pro</div><div class="s-logo-sub">Química · v2.0</div></div>
      </div>
      <nav class="s-nav">
        <div style="margin:4px 6px 3px"><div style="display:flex;align-items:center;gap:7px;padding:6px 8px;border-radius:7px;font-size:11px;color:#4b5563"><span>⊞</span> Dashboard</div></div>
        <div style="height:1px;background:rgba(255,255,255,.05);margin:3px 12px 5px"></div>
        ${depts}
        <div style="height:1px;background:rgba(255,255,255,.05);margin:5px 12px 3px"></div>
        <div class="s-dept it"><div class="s-dept-icon" style="background:rgba(99,102,241,.2)">🖥️</div><div class="s-dept-name">Admin. Sistemas</div></div>
        <div class="it-track">${itItems}</div>
      </nav>
      <div class="s-footer">
        <div class="s-user">
          <div class="s-avatar">JG</div>
          <div><div class="s-uname">Jorge García</div><div class="s-urole">Admin. Sistemas</div></div>
          <div class="s-dot"></div>
        </div>
      </div>
    </aside>`;
}

function page(activeItem, title, bc, btns, content) {
  return `<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
  <title>${title}</title>
  <style>${CSS}</style></head><body>
  ${sidebar(activeItem)}
  <div class="main">
    <header class="topbar">
      <div class="tb-title">${title}</div>
      <div class="tb-bc">Admin. Sistemas › <span>${bc}</span></div>
      ${btns}
    </header>
    <div class="content">${content}</div>
  </div>
  </body></html>`;
}

// ─── PAGE DEFINITIONS ────────────────────────────────────────────────────────

const pages = {

'01_usuarios': page('Usuarios del sistema','👤 Usuarios del sistema','Usuarios',
`<button class="tb-btn btn-pri">+ Nuevo usuario</button>
 <button class="tb-btn btn-sec">📤 Importar</button>`,
`<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
  <div>
    <div class="page-title">Usuarios del sistema</div>
    <div class="page-sub">612 usuarios registrados · 84 activos ahora</div>
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <div class="search"><span style="color:#374151">🔍</span><input placeholder="Nombre, email, dpto..."></div>
    <div class="filters">
      <span class="filter-btn active">Todos</span>
      <span class="filter-btn">Activos</span>
      <span class="filter-btn">Inactivos</span>
    </div>
  </div>
</div>
<div class="card" style="padding:0;overflow:hidden">
<table class="t">
<thead style="background:rgba(0,0,0,.2)"><tr>
  <th style="padding:10px 12px">Nombre</th><th>Email</th><th>Departamento</th><th>Rol</th><th>Último acceso</th><th>Estado</th><th>Acciones</th>
</tr></thead>
<tbody>
<tr><td class="emp" style="padding-left:12px">Ana Martínez</td><td>a.martinez@empresa.com</td><td>🏭 Almacén</td><td><span class="badge pur">Jefe almacén</span></td><td>Hace 12 min</td><td><span class="badge ok">● Activo</span></td><td><span style="color:#6366f1;font-size:11px;cursor:pointer">Editar</span></td></tr>
<tr><td class="emp" style="padding-left:12px">Pedro González</td><td>p.gonzalez@empresa.com</td><td>⚗️ Producción</td><td><span class="badge inf">Operario</span></td><td>Hace 3 h</td><td><span class="badge ok">● Activo</span></td><td><span style="color:#6366f1;font-size:11px;cursor:pointer">Editar</span></td></tr>
<tr><td class="emp" style="padding-left:12px">Laura Ruiz</td><td>l.ruiz@empresa.com</td><td>🔬 Calidad</td><td><span class="badge warn">Supervisor</span></td><td>Ayer 16:30</td><td><span class="badge ok">● Activo</span></td><td><span style="color:#6366f1;font-size:11px;cursor:pointer">Editar</span></td></tr>
<tr><td class="emp" style="padding-left:12px">Miguel López</td><td>m.lopez@empresa.com</td><td>🛒 Compras</td><td><span class="badge inf">Técnico</span></td><td>Hace 1 h</td><td><span class="badge ok">● Activo</span></td><td><span style="color:#6366f1;font-size:11px;cursor:pointer">Editar</span></td></tr>
<tr><td class="emp" style="padding-left:12px">Sara Torres</td><td>s.torres@empresa.com</td><td>👥 RRHH</td><td><span class="badge pur">Responsable</span></td><td>Hace 30 min</td><td><span class="badge ok">● Activo</span></td><td><span style="color:#6366f1;font-size:11px;cursor:pointer">Editar</span></td></tr>
<tr><td class="emp" style="padding-left:12px">Carlos Vega</td><td>c.vega@empresa.com</td><td>🔧 Mantenimiento</td><td><span class="badge inf">Técnico</span></td><td>Hace 5 días</td><td><span class="badge warn">⏸ Baja temporal</span></td><td><span style="color:#6366f1;font-size:11px;cursor:pointer">Editar</span></td></tr>
<tr><td class="emp" style="padding-left:12px">Rosa Navarro</td><td>r.navarro@empresa.com</td><td>📦 Ventas</td><td><span class="badge inf">Comercial</span></td><td>Nunca</td><td><span class="badge err">○ Inactivo</span></td><td><span style="color:#6366f1;font-size:11px;cursor:pointer">Editar</span></td></tr>
</tbody>
</table>
</div>
<div style="display:flex;align-items:center;justify-content:space-between;margin-top:12px;font-size:11px;color:#4b5563">
  <span>Mostrando 1–7 de 612 usuarios</span>
  <div style="display:flex;gap:4px">
    <span class="filter-btn">‹</span><span class="filter-btn active">1</span><span class="filter-btn">2</span><span class="filter-btn">3</span><span class="filter-btn">…</span><span class="filter-btn">87</span><span class="filter-btn">›</span>
  </div>
</div>`),

'02_roles': page('Roles y perfiles','🎭 Roles y perfiles','Roles',
`<button class="tb-btn btn-pri">+ Nuevo rol</button>`,
`<div class="page-header">
  <div><div class="page-title">Roles y perfiles</div><div class="page-sub">Define qué puede hacer cada tipo de usuario en la aplicación</div></div>
</div>
<div class="grid2" style="gap:10px">
${[
  ['🖥️','Administrador de Sistemas','Acceso total a todos los módulos y configuración','4 usuarios','rgba(99,102,241,.2)','#a5b4fc','✓ Ver  ✓ Crear  ✓ Editar  ✓ Eliminar  ✓ Config.'],
  ['🏭','Jefe de Almacén','Gestión completa de logística, inventario y movimientos','12 usuarios','rgba(6,182,212,.15)','#67e8f9','✓ Ver  ✓ Crear  ✓ Editar  ✗ Eliminar  ✗ Config.'],
  ['⚗️','Responsable de Producción','Fórmulas, órdenes de fabricación y planificación','8 usuarios','rgba(16,185,129,.15)','#34d399','✓ Ver  ✓ Crear  ✓ Editar  ✗ Eliminar  ✗ Config.'],
  ['🔬','Técnico de Calidad','Control de calidad, análisis y no conformidades','6 usuarios','rgba(239,68,68,.15)','#f87171','✓ Ver  ✓ Crear  ✓ Editar  ✗ Eliminar  ✗ Config.'],
  ['🛒','Responsable de Compras','Proveedores, OC y precios. Sin acceso a producción','5 usuarios','rgba(245,158,11,.15)','#fcd34d','✓ Ver  ✓ Crear  ✓ Editar  ✗ Eliminar  ✗ Config.'],
  ['👤','Operario de Almacén','Solo registro de movimientos y consulta de stock','340 usuarios','rgba(75,85,99,.3)','#9ca3af','✓ Ver  ✓ Crear  ✗ Editar  ✗ Eliminar  ✗ Config.'],
  ['👥','RRHH','Empleados, turnos, vacaciones y nóminas','7 usuarios','rgba(139,92,246,.15)','#c4b5fd','✓ Ver  ✓ Crear  ✓ Editar  ✗ Eliminar  ✗ Config.'],
  ['📊','Dirección','Solo lectura de todos los módulos + informes ejecutivos','15 usuarios','rgba(251,191,36,.15)','#fde68a','✓ Ver  ✗ Crear  ✗ Editar  ✗ Eliminar  ✗ Config.'],
].map(([ic,name,desc,users,bg,col,perms])=>`
  <div class="card" style="display:flex;flex-direction:column;gap:8px;border-color:${bg}">
    <div style="display:flex;align-items:center;gap:8px">
      <div style="width:28px;height:28px;border-radius:8px;background:${bg};display:flex;align-items:center;justify-content:center;font-size:14px">${ic}</div>
      <div style="flex:1"><div style="font-size:12.5px;font-weight:700;color:#e2e8f0">${name}</div><div style="font-size:10px;color:#4b5563">${users}</div></div>
      <span style="font-size:11px;color:#6366f1;cursor:pointer">Editar</span>
    </div>
    <div style="font-size:11px;color:#6b7280">${desc}</div>
    <div style="font-size:10px;color:${col};background:rgba(0,0,0,.2);border-radius:5px;padding:5px 8px">${perms}</div>
  </div>`).join('')}
</div>`),

'03_permisos': page('Permisos por departamento','🔑 Permisos por departamento','Permisos',
`<button class="tb-btn btn-sec">💾 Guardar cambios</button>`,
`<div class="page-header">
  <div><div class="page-title">Matriz de permisos por departamento</div><div class="page-sub">Controla qué puede hacer cada rol en cada sección</div></div>
  <div class="filters"><span class="filter-btn active">Todos los roles</span><span class="filter-btn">Solo operarios</span></div>
</div>
<div class="card" style="padding:0;overflow:hidden">
<table class="t">
<thead style="background:rgba(0,0,0,.25)"><tr>
  <th style="padding:10px 14px;min-width:160px">Módulo</th>
  ${['Admin Sis.','J. Almacén','Producción','Calidad','Compras','Operario','RRHH','Dirección'].map(r=>`<th style="text-align:center;font-size:9.5px">${r}</th>`).join('')}
</tr></thead>
<tbody>
${[
  ['🏭 Almacén & Logística', [1,1,0,0,0,1,0,0]],
  ['⚗️ Producción','','',1,[1,0,1,0,0,0,0,0]],
  ['🛒 Compras & Aprovisionamiento',  [1,0,0,0,1,0,0,0]],
  ['📦 Ventas & Distribución',        [1,0,0,0,1,0,0,1]],
  ['🔬 Calidad & Regulatorio',        [1,0,0,1,0,0,0,1]],
  ['👥 Recursos Humanos',             [1,0,0,0,0,0,1,1]],
  ['🔧 Mantenimiento',                [1,1,0,0,0,0,0,0]],
  ['📊 Dirección & Informes',         [1,0,0,0,0,0,0,1]],
  ['🖥️ Admin. Sistemas',             [1,0,0,0,0,0,0,0]],
].map(([mod, checks])=>{
  const c = Array.isArray(checks) ? checks : [1,0,0,0,0,0,0,0];
  const all = [1,...c]; // Admin always has all
  // override: admin (col 0) = always 1
  all[0]=1;
  return `<tr>
    <td class="emp" style="padding-left:14px;font-size:11.5px">${mod}</td>
    ${all.slice(0,8).map((v,i)=>`<td style="text-align:center"><div class="check ${i===0?'chk-on':(v?'chk-on':'chk-off')}" style="margin:auto">${i===0||v?'✓':''}</div></td>`).join('')}
  </tr>`;
}).join('')}
</tbody>
</table>
</div>
<div style="margin-top:10px;padding:10px 14px;border-radius:8px;background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);font-size:11px;color:#a5b4fc">
  🔓 El perfil <strong>Admin. Sistemas</strong> tiene acceso total garantizado y no puede ser restringido desde esta pantalla.
</div>`),

'04_ldap': page('Control de accesos AD/LDAP','🔐 Control accesos AD/LDAP','AD / LDAP',
`<button class="tb-btn btn-pri">🔄 Sincronizar ahora</button>
 <button class="tb-btn btn-sec">🧪 Probar conexión</button>`,
`<div class="grid2">
  <div style="display:flex;flex-direction:column;gap:10px">
    <div class="card">
      <div class="card-title">🔌 Conexión al directorio</div>
      <div style="display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.2);margin-bottom:12px">
        <div class="status-dot sd-on"></div>
        <div style="font-size:12px;color:#10b981;font-weight:600">Conectado al servidor LDAP corporativo</div>
        <div style="margin-left:auto;font-size:10px;color:#4b5563">Último sync: hace 4 min</div>
      </div>
      <div class="form-group"><label>Servidor LDAP / AD</label><input type="text" value="ldap://dc01.empresa.local:389"></div>
      <div class="form-row">
        <div class="form-group"><label>Base DN</label><input type="text" value="DC=empresa,DC=local"></div>
        <div class="form-group"><label>Bind DN</label><input type="text" value="CN=srv-app,OU=ServiceAccounts"></div>
      </div>
      <div class="form-group"><label>Contraseña de servicio</label><input type="text" value="••••••••••••"></div>
    </div>
    <div class="card">
      <div class="card-title">⏱️ Sincronización automática</div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
        <div><div style="font-size:12px;color:#d1d5db;font-weight:500">Sincronizar usuarios automáticamente</div><div style="font-size:10px;color:#4b5563">Importa nuevos usuarios y cambios del AD</div></div>
        <div class="toggle on"></div>
      </div>
      <div class="form-group"><label>Frecuencia de sync</label><select><option>Cada 15 minutos</option></select></div>
    </div>
  </div>
  <div style="display:flex;flex-direction:column;gap:10px">
    <div class="card">
      <div class="card-title">🗂️ Grupos del AD → Roles de la app</div>
      ${[
        ['GRP_ALMACEN','Operario de Almacén','340 usuarios','ok'],
        ['GRP_JEFES_ALM','Jefe de Almacén','12 usuarios','ok'],
        ['GRP_PRODUCCION','Responsable Producción','8 usuarios','ok'],
        ['GRP_CALIDAD','Técnico de Calidad','6 usuarios','ok'],
        ['GRP_COMPRAS','Responsable de Compras','5 usuarios','ok'],
        ['GRP_RRHH','RRHH','7 usuarios','ok'],
        ['GRP_IT','Administrador de Sistemas','4 usuarios','ok'],
        ['GRP_DIRECCION','Dirección (solo lectura)','15 usuarios','warn'],
      ].map(([grp,rol,users,st])=>`
        <div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-top:1px solid rgba(255,255,255,.04)">
          <div style="flex:1">
            <div style="font-size:11.5px;color:#d1d5db;font-weight:500">${grp}</div>
            <div style="font-size:10px;color:#4b5563">→ ${rol} · ${users}</div>
          </div>
          <span class="badge ${st}">${st==='ok'?'Mapeado':'⚠ Sin mapear'}</span>
        </div>`).join('')}
    </div>
    <div class="card">
      <div class="card-title">📋 Últimas sincronizaciones</div>
      ${[['Hace 4 min','✅ OK — 2 usuarios nuevos'],['Hace 19 min','✅ OK — sin cambios'],['Hace 34 min','✅ OK — 1 usuario desactivado'],['Hace 1h','⚠ Warn — timeout en DC02']].map(([t,m])=>`
        <div style="display:flex;gap:8px;font-size:11px;padding:5px 0;border-top:1px solid rgba(255,255,255,.04)">
          <span style="color:#374151;min-width:75px">${t}</span><span style="color:#9ca3af">${m}</span>
        </div>`).join('')}
    </div>
  </div>
</div>`),

'05_config': page('Configuración general','⚙️ Configuración general','Configuración',
`<button class="tb-btn btn-pri">💾 Guardar cambios</button>`,
`<div class="grid2" style="gap:12px">
  <div style="display:flex;flex-direction:column;gap:10px">
    <div class="card">
      <div class="card-title">🏢 Datos de la empresa</div>
      <div class="form-group"><label>Nombre de la empresa</label><input type="text" value="Química del Sur, S.L."></div>
      <div class="form-row">
        <div class="form-group"><label>NIF / CIF</label><input type="text" value="B-12345678"></div>
        <div class="form-group"><label>Teléfono</label><input type="text" value="+34 955 123 456"></div>
      </div>
      <div class="form-group"><label>Dirección</label><input type="text" value="Pol. Ind. Sur, C/ Química 14, Sevilla"></div>
    </div>
    <div class="card">
      <div class="card-title">🌍 Localización y formato</div>
      <div class="form-row">
        <div class="form-group"><label>Idioma de la app</label><select><option>Español</option></select></div>
        <div class="form-group"><label>Zona horaria</label><select><option>Europe/Madrid (UTC+2)</option></select></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Formato de fecha</label><select><option>DD/MM/YYYY</option></select></div>
        <div class="form-group"><label>Moneda</label><select><option>EUR (€)</option></select></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">🔒 Seguridad de sesión</div>
      <div class="form-row">
        <div class="form-group"><label>Tiempo de inactividad</label><select><option>30 minutos</option></select></div>
        <div class="form-group"><label>Intentos de login</label><select><option>5 intentos</option></select></div>
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:4px">
        <div><div style="font-size:12px;color:#d1d5db">Autenticación en dos pasos (2FA)</div><div style="font-size:10px;color:#4b5563">Para roles de administración</div></div>
        <div class="toggle on"></div>
      </div>
    </div>
  </div>
  <div style="display:flex;flex-direction:column;gap:10px">
    <div class="card">
      <div class="card-title">🔔 Notificaciones del sistema</div>
      ${[
        ['Alertas de stock mínimo','Notificar a Compras automáticamente',true],
        ['Caducidades próximas','Avisar con 30 días de antelación',true],
        ['No conformidades de calidad','Alertar a responsable de dpto.',true],
        ['Fallos de backup','Notificar por email a IT',true],
        ['Nuevos usuarios registrados','Resumen diario a IT',false],
      ].map(([t,s,on])=>`
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-top:1px solid rgba(255,255,255,.04)">
          <div><div style="font-size:12px;color:#d1d5db">${t}</div><div style="font-size:10px;color:#4b5563">${s}</div></div>
          <div class="toggle ${on?'on':'off'}"></div>
        </div>`).join('')}
    </div>
    <div class="card">
      <div class="card-title">📧 Servidor de correo (SMTP)</div>
      <div class="form-group"><label>Servidor SMTP</label><input type="text" value="mail.empresa.local"></div>
      <div class="form-row">
        <div class="form-group"><label>Puerto</label><input type="number" value="587"></div>
        <div class="form-group"><label>Remitente</label><input type="email" value="noreply@empresa.com"></div>
      </div>
      <div style="display:flex;align-items:center;gap:6px;margin-top:6px">
        <div class="status-dot sd-on"></div>
        <span style="font-size:11px;color:#10b981">Conexión SMTP verificada</span>
      </div>
    </div>
  </div>
</div>`),

'06_monitor': page('Monitor del sistema','📊 Monitor del sistema','Monitor',
`<button class="tb-btn btn-sec">🔄 Actualizar</button>`,
`<div class="grid4" style="margin-bottom:12px">
${[
  ['💻','CPU','23%','rgba(6,182,212,.12)','rgba(6,182,212,.7)',23,'Normal'],
  ['🧠','RAM','67%','rgba(245,158,11,.12)','rgba(245,158,11,.7)',67,'Moderado'],
  ['💽','Disco','41%','rgba(16,185,129,.12)','rgba(16,185,129,.7)',41,'Normal'],
  ['🌐','Red','12 MB/s','rgba(99,102,241,.12)','rgba(99,102,241,.7)',12,'Normal'],
].map(([ic,l,v,bg,col,pct,st])=>`
  <div class="kpi">
    <div class="kpi-i" style="background:${bg}">${ic}</div>
    <div class="kpi-l">${l}</div>
    <div class="kpi-v">${v}</div>
    <div class="prog-bar"><div class="prog-fill" style="width:${pct}%;background:${col}"></div></div>
    <div class="kpi-s" style="margin-top:4px">${st}</div>
  </div>`).join('')}
</div>
<div class="grid2" style="gap:12px">
  <div style="display:flex;flex-direction:column;gap:10px">
    <div class="card">
      <div class="card-title">⏱️ Estado del servidor</div>
      ${[
        ['Tiempo activo (uptime)','47 días, 12h 34min','ok'],
        ['Versión de la app','v2.0.14 (última)','ok'],
        ['Base de datos','SQLite 3.42 · 2.3 GB','ok'],
        ['Último backup','Hoy 03:00 — 847 MB','ok'],
        ['Tareas programadas','6 activas','inf'],
        ['Sesiones abiertas ahora','84 usuarios','inf'],
      ].map(([k,v,st])=>`
        <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-top:1px solid rgba(255,255,255,.04)">
          <span style="font-size:11.5px;color:#6b7280">${k}</span>
          <span class="badge ${st}">${v}</span>
        </div>`).join('')}
    </div>
    <div class="card">
      <div class="card-title">📊 Sesiones activas por departamento</div>
      ${[['🏭 Almacén',42,50],['⚗️ Producción',18,20],['🔬 Calidad',8,15],['🛒 Compras',7,10],['👥 RRHH',5,8],['📦 Ventas',4,12]].map(([d,a,t])=>`
        <div style="margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;margin-bottom:3px">
            <span style="font-size:11.5px;color:#d1d5db">${d}</span>
            <span style="font-size:11px;color:#6b7280">${a}/${t}</span>
          </div>
          <div class="prog-bar"><div class="prog-fill" style="width:${Math.round(a/t*100)}%;background:linear-gradient(90deg,#6366f1,#8b5cf6)"></div></div>
        </div>`).join('')}
    </div>
  </div>
  <div style="display:flex;flex-direction:column;gap:10px">
    <div class="card">
      <div class="card-title">⚡ Tiempos de respuesta (ms)</div>
      <div style="display:flex;align-items:flex-end;gap:5px;height:100px;padding-bottom:4px;margin-bottom:6px">
        ${[45,62,38,71,55,48,80,43,39,52,47,60].map(v=>`
          <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">
            <div style="flex:1;width:100%;display:flex;align-items:flex-end">
              <div style="width:100%;border-radius:3px 3px 0 0;background:linear-gradient(180deg,#6366f1,rgba(99,102,241,.3))" data-h="${v}"></div>
            </div>
          </div>`).join('')}
      </div>
      <div style="font-size:10px;color:#4b5563;text-align:center">Últimas 12 horas · Promedio: 52ms</div>
    </div>
    <div class="card">
      <div class="card-title">🔥 Procesos en ejecución</div>
      ${[
        ['Servidor web','Puerto 8080','Running','ok'],
        ['Sincronización LDAP','Cada 15 min','Running','ok'],
        ['Backup automático','Diario 03:00','Scheduled','inf'],
        ['Limpieza de logs','Semanal','Scheduled','inf'],
        ['Monitor de caducidades','Cada hora','Running','ok'],
        ['Cola de notificaciones','Tiempo real','Running','ok'],
      ].map(([p,d,st,b])=>`
        <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-top:1px solid rgba(255,255,255,.04)">
          <div class="status-dot ${st==='Running'?'sd-on':'sd-warn'}"></div>
          <div style="flex:1"><div style="font-size:11.5px;color:#d1d5db">${p}</div><div style="font-size:10px;color:#374151">${d}</div></div>
          <span class="badge ${b}">${st}</span>
        </div>`).join('')}
    </div>
  </div>
</div>`),

'07_logs': page('Logs de actividad','📜 Logs de actividad','Logs',
`<button class="tb-btn btn-sec">📤 Exportar</button>
 <button class="tb-btn btn-sec">🗑️ Limpiar antiguos</button>`,
`<div style="display:flex;gap:8px;align-items:center;margin-bottom:14px">
  <div class="search" style="width:220px"><span style="color:#374151">🔍</span><input placeholder="Usuario, módulo, acción..."></div>
  <div class="filters">
    <span class="filter-btn active">Todos</span>
    <span class="filter-btn">⚠ Alertas</span>
    <span class="filter-btn">❌ Errores</span>
    <span class="filter-btn">🔐 Accesos</span>
    <span class="filter-btn">✏️ Cambios</span>
  </div>
  <input type="text" value="07/06/2026" style="width:110px">
</div>
<div class="card" style="padding:0;overflow:hidden">
<table class="t">
<thead style="background:rgba(0,0,0,.2)"><tr>
  <th style="padding:9px 12px">Hora</th><th>Nivel</th><th>Usuario</th><th>Departamento</th><th>Módulo</th><th>Acción</th><th>IP</th>
</tr></thead>
<tbody>
${[
  ['13:42:11','INFO','a.martinez','Almacén','Entradas','Registro entrada lote LT-2241 — 500 kg Lauril','192.168.1.45'],
  ['13:39:07','WARN','sistema','Sistema','Inventario','REF MP-0312 alcanzó stock mínimo (3 kg)','—'],
  ['13:35:22','INFO','j.garcia','IT','Usuarios','Nuevo usuario creado: m.torres@empresa.com','192.168.1.2'],
  ['13:28:45','ERROR','l.ruiz','Calidad','Análisis','Error exportando informe PDF — timeout','192.168.1.88'],
  ['13:21:03','INFO','p.gonzalez','Producción','OF','OF-2341 marcada como completada','192.168.1.67'],
  ['13:15:50','INFO','s.torres','RRHH','Empleados','Solicitud vacaciones aprobada — C.Vega','192.168.1.91'],
  ['13:08:33','WARN','sistema','Backup','Auto-backup','Backup tardó más de 10 min — 847 MB','—'],
  ['13:01:19','INFO','m.lopez','Compras','OC','OC-5521 enviada a proveedor QuímicaSur','192.168.1.77'],
  ['12:55:44','ERROR','r.navarro','Acceso','Login','Intento de acceso fallido (3/5)','192.168.1.200'],
  ['12:48:12','INFO','sistema','LDAP','Sync','Sincronización OK — 1 usuario nuevo importado','—'],
].map(([t,lvl,usr,dept,mod,msg,ip])=>{
  const b = lvl==='ERROR'?'err':lvl==='WARN'?'warn':'inf';
  return `<tr>
    <td style="padding-left:12px;font-size:11px;color:#4b5563;font-family:monospace">${t}</td>
    <td><span class="badge ${b}">${lvl}</span></td>
    <td class="emp">${usr}</td>
    <td style="font-size:11px">${dept}</td>
    <td style="font-size:11px;color:#6b7280">${mod}</td>
    <td style="font-size:11.5px;max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${msg}</td>
    <td style="font-size:10.5px;color:#374151;font-family:monospace">${ip}</td>
  </tr>`;}).join('')}
</tbody>
</table>
</div>
<div style="display:flex;justify-content:space-between;margin-top:10px;font-size:11px;color:#4b5563">
  <span>1,247 eventos hoy · 47 alertas pendientes de revisión</span>
  <span>Auto-refresco: cada 30 s</span>
</div>`),

'08_auditoria': page('Auditoría de cambios','🕵️ Auditoría de cambios','Auditoría',
`<button class="tb-btn btn-sec">📤 Exportar</button>`,
`<div style="display:flex;gap:8px;margin-bottom:14px;align-items:center">
  <div class="search"><span style="color:#374151">🔍</span><input placeholder="Campo, módulo, usuario..."></div>
  <div class="filters">
    <span class="filter-btn active">Todos</span><span class="filter-btn">Creaciones</span><span class="filter-btn">Ediciones</span><span class="filter-btn">Eliminaciones</span>
  </div>
</div>
<div class="card" style="padding:0;overflow:hidden">
<table class="t">
<thead style="background:rgba(0,0,0,.2)"><tr>
  <th style="padding:9px 12px">Fecha / Hora</th><th>Usuario</th><th>Módulo</th><th>Registro</th><th>Campo</th><th>Valor anterior</th><th>Valor nuevo</th><th>Tipo</th>
</tr></thead>
<tbody>
${[
  ['07/06 13:35','j.garcia','Usuarios','m.torres@empresa.com','—','—','Nuevo registro','ok'],
  ['07/06 13:21','p.gonzalez','Producción OF','OF-2341','Estado','En proceso','Completada','warn'],
  ['07/06 13:08','a.martinez','Inventario','MP-0421 Lauril sulfato','Stock','1.200 kg','1.700 kg','ok'],
  ['07/06 12:55','l.ruiz','Calidad NC','NC-0042','Severidad','Media','Alta','warn'],
  ['07/06 12:30','s.torres','RRHH Empleados','C.Vega','Estado','Activo','Baja temporal','warn'],
  ['07/06 11:45','m.lopez','Compras OC','OC-5521','Estado','Borrador','Enviada','ok'],
  ['07/06 11:12','j.garcia','Roles','Operario Almacén','Permiso editar','Sí','No','err'],
  ['07/06 10:55','a.martinez','Inventario','MP-0312 Fragancia','Stock mínimo','20 kg','50 kg','warn'],
].map(([dt,usr,mod,reg,campo,ant,nue,t])=>`<tr>
  <td style="padding-left:12px;font-size:10.5px;color:#4b5563;font-family:monospace">${dt}</td>
  <td class="emp">${usr}</td>
  <td style="font-size:11px">${mod}</td>
  <td style="font-size:11px;color:#6b7280">${reg}</td>
  <td style="font-size:11px;color:#9ca3af">${campo}</td>
  <td style="font-size:11px;color:#ef4444;text-decoration:line-through">${ant}</td>
  <td style="font-size:11px;color:#10b981">${nue}</td>
  <td><span class="badge ${t}">${t==='ok'?'Creación':t==='warn'?'Edición':'Eliminación'}</span></td>
</tr>`).join('')}
</tbody>
</table>
</div>`),

'09_backup': page('Copias de seguridad','💾 Copias de seguridad','Backups',
`<button class="tb-btn btn-pri">▶ Backup manual</button>`,
`<div class="grid2" style="gap:12px">
  <div style="display:flex;flex-direction:column;gap:10px">
    <div class="card">
      <div class="card-title">📅 Programación de backups</div>
      ${[
        ['Backup completo diario','Cada día a las 03:00','Activo','ok','Próximo: mañana 03:00'],
        ['Backup incremental','Cada 6 horas','Activo','ok','Próximo: 18:00'],
        ['Backup semanal (completo)','Domingos a las 01:00','Activo','ok','Próximo: dom 01:00'],
      ].map(([n,s,st,b,p])=>`
        <div style="padding:10px 12px;border-radius:8px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);margin-bottom:8px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
            <div style="font-size:12.5px;font-weight:600;color:#d1d5db">${n}</div>
            <span class="badge ${b}">${st}</span>
          </div>
          <div style="font-size:11px;color:#4b5563">${s} · <span style="color:#6b7280">${p}</span></div>
        </div>`).join('')}
      <div class="sep"></div>
      <div class="form-group"><label>Destino del backup</label><input type="text" value="\\\\fileserver\backups\gestoralmacen"></div>
      <div class="form-row">
        <div class="form-group"><label>Retención (días)</label><input type="number" value="30"></div>
        <div class="form-group"><label>Compresión</label><select><option>ZIP (alta)</option></select></div>
      </div>
    </div>
  </div>
  <div style="display:flex;flex-direction:column;gap:10px">
    <div class="card">
      <div class="card-title">📋 Historial de copias</div>
      ${[
        ['Hoy 03:00','Completo','847 MB','✅ Correcto','ok'],
        ['Ayer 21:00','Incremental','124 MB','✅ Correcto','ok'],
        ['Ayer 15:00','Incremental','98 MB','✅ Correcto','ok'],
        ['Ayer 09:00','Incremental','203 MB','✅ Correcto','ok'],
        ['Ayer 03:00','Completo','831 MB','✅ Correcto','ok'],
        ['02/06 03:00','Completo','819 MB','⚠ Lento (12 min)','warn'],
        ['01/06/2026','Semanal','3.2 GB','✅ Correcto','ok'],
        ['25/05/2026','Semanal','3.0 GB','❌ Error — sin espacio','err'],
      ].map(([dt,tipo,tam,st,b])=>`
        <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-top:1px solid rgba(255,255,255,.04)">
          <div style="flex:1">
            <div style="font-size:11.5px;color:#d1d5db;font-weight:500">${dt} — ${tipo}</div>
            <div style="font-size:10px;color:#374151">${tam}</div>
          </div>
          <span class="badge ${b}">${st}</span>
          <span style="font-size:11px;color:#6366f1;cursor:pointer">⬇</span>
        </div>`).join('')}
    </div>
  </div>
</div>`),

'10_bbdd': page('Base de datos','🗄️ Base de datos','Base de datos',
`<button class="tb-btn btn-sec">🔧 Mantenimiento</button>
 <button class="tb-btn btn-sec">📤 Exportar SQL</button>`,
`<div class="grid4" style="margin-bottom:12px">
${[
  ['🗄️','Tamaño total','2.34 GB',''],
  ['📊','Total de tablas','47',''],
  ['📝','Total de registros','4.2 M',''],
  ['⚡','Tiempo consulta','8 ms','promedio'],
].map(([ic,l,v,s])=>`
  <div class="kpi">
    <div class="kpi-i" style="background:rgba(99,102,241,.12)">${ic}</div>
    <div class="kpi-l">${l}</div>
    <div class="kpi-v">${v}</div>
    <div class="kpi-s">${s}</div>
  </div>`).join('')}
</div>
<div class="grid2">
  <div class="card">
    <div class="card-title">📋 Tablas principales</div>
    <table class="t">
    <thead><tr><th>Tabla</th><th>Registros</th><th>Tamaño</th><th>Última mod.</th></tr></thead>
    <tbody>
    ${[
      ['movimientos','1.842.441','680 MB','hace 3 min'],
      ['inventario','3.847','12 MB','hace 8 min'],
      ['lotes','28.552','45 MB','hace 1 h'],
      ['empleados','612','2 MB','hace 2 h'],
      ['logs_actividad','980.120','312 MB','hace 30 s'],
      ['ordenes_fabricacion','12.443','28 MB','hace 4 h'],
      ['proveedores','248','1 MB','ayer'],
      ['usuarios','612','3 MB','hace 2 h'],
    ].map(([t,r,s,m])=>`<tr><td class="emp">${t}</td><td>${r}</td><td>${s}</td><td style="font-size:10.5px;color:#374151">${m}</td></tr>`).join('')}
    </tbody>
    </table>
  </div>
  <div style="display:flex;flex-direction:column;gap:10px">
    <div class="card">
      <div class="card-title">🔧 Estado y mantenimiento</div>
      ${[
        ['Integridad de datos','✅ Sin errores','ok'],
        ['Índices','✅ Optimizados','ok'],
        ['Fragmentación','⚠ 12% — recomendar VACUUM','warn'],
        ['WAL (write-ahead log)','180 MB — normal','inf'],
        ['Conexiones activas','84 / 200 máx.','inf'],
      ].map(([k,v,b])=>`
        <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-top:1px solid rgba(255,255,255,.04)">
          <span style="font-size:11.5px;color:#6b7280">${k}</span><span class="badge ${b}">${v}</span>
        </div>`).join('')}
      <div style="margin-top:10px;display:flex;gap:8px">
        <button class="tb-btn btn-sec" style="flex:1;font-size:11px">VACUUM</button>
        <button class="tb-btn btn-sec" style="flex:1;font-size:11px">REINDEX</button>
        <button class="tb-btn btn-sec" style="flex:1;font-size:11px">ANALYZE</button>
      </div>
    </div>
    <div class="card">
      <div class="card-title">📊 Crecimiento mensual</div>
      <div style="display:flex;align-items:flex-end;gap:4px;height:60px">
        ${[1.8,1.9,2.0,2.1,2.15,2.2,2.34].map((v,i)=>`
          <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">
            <div style="width:100%;border-radius:3px 3px 0 0;background:${i===6?'linear-gradient(180deg,#6366f1,#8b5cf6)':'rgba(99,102,241,.3)'};height:${Math.round(v/2.34*56)}px"></div>
          </div>`).join('')}
      </div>
      <div style="display:flex;justify-content:space-between;font-size:9.5px;color:#374151;margin-top:4px">
        ${['Dic','Ene','Feb','Mar','Abr','May','Jun'].map(m=>`<span>${m}</span>`).join('')}
      </div>
    </div>
  </div>
</div>`),

'11_dispositivos': page('Dispositivos y terminales','📱 Dispositivos y terminales','Dispositivos',
`<button class="tb-btn btn-pri">+ Registrar dispositivo</button>`,
`<div class="grid4" style="margin-bottom:12px">
${[
  ['💻','PCs de escritorio','28','ok'],
  ['📱','Tablets / PDA','16','ok'],
  ['📷','Lectores código QR','24','ok'],
  ['🖨️','Impresoras etiquetas','8','warn'],
].map(([ic,l,v,st])=>`
  <div class="kpi">
    <div class="kpi-i" style="background:rgba(99,102,241,.12)">${ic}</div>
    <div class="kpi-l">${l}</div>
    <div class="kpi-v">${v}</div>
    <div class="kpi-s"><span class="badge ${st}">${st==='ok'?'Todos online':'1 offline'}</span></div>
  </div>`).join('')}
</div>
<div class="card" style="padding:0;overflow:hidden">
<table class="t">
<thead style="background:rgba(0,0,0,.2)"><tr>
  <th style="padding:9px 12px">Dispositivo</th><th>Tipo</th><th>Ubicación</th><th>Usuario asignado</th><th>IP</th><th>Último acceso</th><th>Estado</th>
</tr></thead>
<tbody>
${[
  ['PC-ALM-01','💻 PC','Almacén — Zona A','a.martinez','192.168.1.45','Hace 12 min','ok'],
  ['TABLET-PROD-03','📱 Tablet','Producción — Línea 2','p.gonzalez','192.168.1.67','Hace 3 min','ok'],
  ['QR-ALM-07','📷 Lector QR','Almacén — Entrada','(sin asignar)','192.168.1.120','Hace 1 min','ok'],
  ['PC-CAL-01','💻 PC','Laboratorio Calidad','l.ruiz','192.168.1.88','Hace 20 min','ok'],
  ['IMP-EXP-02','🖨️ Impresora','Zona Expedición','(compartida)','192.168.1.150','Hace 2 h','warn'],
  ['TABLET-ALM-05','📱 Tablet','Almacén — Zona C','m.torres','192.168.1.72','Hace 5 min','ok'],
  ['QR-PROD-12','📷 Lector QR','Producción — Envasado','(sin asignar)','192.168.1.133','Hace 8 min','ok'],
  ['PC-RRHH-01','💻 PC','Oficina RRHH','s.torres','192.168.1.91','Hace 30 min','ok'],
  ['PC-IT-01','💻 PC','Sala Servidores','j.garcia','192.168.1.2','Hace 2 min','ok'],
  ['TABLET-MANT-01','📱 Tablet','Planta — Libre','c.vega','192.168.1.80','Hace 5 días','err'],
].map(([n,t,u,usr,ip,la,st])=>`<tr>
  <td class="emp" style="padding-left:12px">${n}</td>
  <td style="font-size:11.5px">${t}</td>
  <td style="font-size:11px;color:#6b7280">${u}</td>
  <td style="font-size:11.5px">${usr}</td>
  <td style="font-size:10.5px;color:#374151;font-family:monospace">${ip}</td>
  <td style="font-size:10.5px;color:#4b5563">${la}</td>
  <td><span class="badge ${st}">${st==='ok'?'● Online':st==='warn'?'⚠ Alerta':'○ Offline'}</span></td>
</tr>`).join('')}
</tbody>
</table>
</div>`),

'12_integraciones': page('Integraciones / API','🔗 Integraciones / API','Integraciones',
`<button class="tb-btn btn-pri">+ Nueva integración</button>`,
`<div class="grid2" style="gap:12px">
${[
  ['🏦','ERP Corporativo (SAP B1)','Sincronización de pedidos, facturas y stock con SAP Business One','Conectado · Última sync hace 4 min','ok',
    [['Pedidos de compra','bidireccional','ok'],['Stock e inventario','→ SAP','ok'],['Facturas proveedor','→ SAP','ok']]],
  ['📧','Microsoft 365 / Exchange','Envío de notificaciones, alertas y reportes por correo corporativo','Conectado · SMTP activo','ok',
    [['Alertas de stock','automático','ok'],['Informes diarios','programado','ok'],['Notif. usuarios nuevos','automático','ok']]],
  ['🪪','Active Directory (LDAP)','Autenticación SSO y gestión de usuarios desde el directorio corporativo','Conectado · Sync cada 15 min','ok',
    [['Autenticación SSO','tiempo real','ok'],['Importar usuarios','cada 15 min','ok'],['Grupos → Roles','automático','ok']]],
  ['📊','Power BI / Reporting','Exportación de datos para cuadros de mando ejecutivos en Power BI','Configurado · Push diario 06:00','inf',
    [['KPIs de producción','diario 06:00','ok'],['Informe de stock','diario 06:00','ok'],['Movimientos','tiempo real','warn']]],
  ['🚚','Agencia de transporte (API)','Seguimiento de envíos y generación de etiquetas de envío automáticas','⚠ Error de autenticación — revisar token','err',
    [['Tracking envíos','tiempo real','err'],['Generar etiquetas','automático','err'],['Confirmación entrega','callback','err']]],
  ['🏭','Báscula industrial (IoT)','Lectura automática de pesos en entrada de materia prima vía TCP/IP','Conectado · Puerto 5000','ok',
    [['Lectura automática','tiempo real','ok'],['Registro en entradas','automático','ok'],['Calibración','manual','inf']]],
].map(([ic,name,desc,status,st,conns])=>`
  <div class="card" style="border-color:${st==='err'?'rgba(239,68,68,.2)':st==='inf'?'rgba(6,182,212,.1)':'rgba(255,255,255,.05)'}">
    <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px">
      <div style="width:36px;height:36px;border-radius:9px;background:rgba(255,255,255,.06);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">${ic}</div>
      <div style="flex:1">
        <div style="font-size:13px;font-weight:700;color:#e2e8f0">${name}</div>
        <div style="font-size:10.5px;color:#4b5563;margin-top:2px;line-height:1.4">${desc}</div>
      </div>
      <span class="badge ${st}" style="flex-shrink:0">${st==='ok'?'● Activo':st==='err'?'❌ Error':'⚙ Config.'}</span>
    </div>
    <div style="padding:7px 10px;border-radius:7px;background:rgba(0,0,0,.2);font-size:10.5px;color:${st==='err'?'#f87171':st==='inf'?'#67e8f9':'#6b7280'};margin-bottom:10px">${status}</div>
    <div style="display:flex;flex-direction:column;gap:4px">
      ${conns.map(([f,m,b])=>`
        <div style="display:flex;align-items:center;justify-content:space-between;font-size:11px">
          <span style="color:#9ca3af">${f}</span>
          <div style="display:flex;align-items:center;gap:6px">
            <span style="color:#374151">${m}</span>
            <span class="badge ${b}" style="padding:1px 5px">${b==='ok'?'OK':b==='warn'?'Lento':'Error'}</span>
          </div>
        </div>`).join('')}
    </div>
  </div>`).join('')}
</div>`),

};

// ─── Screenshot all pages ─────────────────────────────────────────────────────
(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox','--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 800 });

  for (const [name, html] of Object.entries(pages)) {
    const htmlPath = path.join(OUT, `${name}.html`);
    fs.writeFileSync(htmlPath, html);
    await page.goto('file://' + htmlPath);
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(OUT, `${name}.png`) });
    console.log(`✓ ${name}`);
  }

  await browser.close();
  console.log('All done.');
})();
