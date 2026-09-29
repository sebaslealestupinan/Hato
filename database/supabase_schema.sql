-- =====================================================================
-- HATO · Gestión y trazabilidad de ganado
-- Esquema para Supabase (PostgreSQL) + bucket de fotos
-- Ejecutar completo en: Supabase Dashboard → SQL Editor → New query
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. TABLAS
-- ---------------------------------------------------------------------

-- Fincas (antes: fincas)
create table if not exists public.fincas (
    id                bigint generated always as identity primary key,
    nombre            varchar(100) not null,
    tamano_hectareas  numeric(10,2) not null check (tamano_hectareas > 0),
    ubicacion         varchar(200) not null,
    creada_por        uuid references auth.users(id) on delete set null,
    created_at        timestamptz not null default now()
);

-- Quién tiene acceso a cada finca (permite "compartir el mismo hato entre dos personas")
create table if not exists public.finca_miembros (
    finca_id   bigint not null references public.fincas(id) on delete cascade,
    user_id    uuid   not null references auth.users(id)   on delete cascade,
    rol        text   not null default 'encargado'
               check (rol in ('propietario','encargado','veterinario')),
    created_at timestamptz not null default now(),
    primary key (finca_id, user_id)
);

-- Tipos de animal (antes: tipos_animales)
create table if not exists public.tipos_animales (
    id     bigint generated always as identity primary key,
    nombre varchar(60) not null unique
);

-- Animales (antes: ganados)
create table if not exists public.animales (
    id               bigint generated always as identity primary key,

    -- Identificador que va en el código QR: no adivinable, no cambia nunca
    codigo_publico   uuid not null unique default gen_random_uuid(),

    -- Arete / identificación que escribe el ganadero
    identificacion   varchar(50) not null,
    nombre           varchar(100),
    sexo             text not null check (sexo in ('Macho','Hembra')),
    raza             varchar(80),
    fecha_nacimiento date not null check (fecha_nacimiento <= current_date),
    estado           text not null default 'Activo' check (estado in ('Activo','Vendido','Fallecido','Descarte','Cuarentena')),

    finca_id         bigint not null references public.fincas(id) on delete cascade,
    tipo_animal_id   bigint not null references public.tipos_animales(id) on delete restrict,
    madre_id         bigint references public.animales(id) on delete set null,
    padre_id         bigint references public.animales(id) on delete set null,

    -- Ruta del archivo dentro del bucket (NO la URL). Ej: 3/17/foto.jpg
    foto_path        text,

    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now(),

    -- Evita duplicados: no puede haber dos animales con el mismo arete en la misma finca
    constraint animales_identificacion_unica_por_finca unique (finca_id, identificacion)
);

create index if not exists idx_animales_finca  on public.animales (finca_id);
create index if not exists idx_animales_tipo   on public.animales (tipo_animal_id);
create index if not exists idx_animales_estado on public.animales (estado);

-- Historial de controles y novedades (vacunas, tratamientos, pesajes, etc.)
create table if not exists public.eventos_animal (
    id             bigint generated always as identity primary key,
    animal_id      bigint not null references public.animales(id) on delete cascade,
    tipo           text not null
                   check (tipo in ('vacunacion','desparasitacion','tratamiento','parto','inseminacion','novedad','vacuna','control_veterinario','pesaje')),
    descripcion    text not null,
    fecha_evento   date not null default current_date,
    proximo_control date,                      -- base para alertas
    registrado_por uuid references auth.users(id) on delete set null,
    created_at     timestamptz not null default now()
);

create index if not exists idx_eventos_animal        on public.eventos_animal (animal_id, fecha_evento desc);
create index if not exists idx_eventos_proximo       on public.eventos_animal (proximo_control)
    where proximo_control is not null;

-- La edad se calcula, no se guarda (así nunca queda desactualizada)
create or replace view public.animales_con_edad
with (security_invoker = true) as
select
    a.*,
    (extract(year  from age(current_date, a.fecha_nacimiento)) * 12
   + extract(month from age(current_date, a.fecha_nacimiento)))::int as edad_meses
from public.animales a;

-- updated_at automático
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end $$;

drop trigger if exists trg_animales_updated_at on public.animales;
create trigger trg_animales_updated_at
before update on public.animales
for each row execute function public.set_updated_at();

-- Al crear una finca, quien la crea queda como propietario
create or replace function public.finca_owner_membership()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    if new.creada_por is not null then
        insert into public.finca_miembros (finca_id, user_id, rol)
        values (new.id, new.creada_por, 'propietario')
        on conflict do nothing;
    end if;
    return new;
end $$;

drop trigger if exists trg_finca_owner on public.fincas;
create trigger trg_finca_owner
after insert on public.fincas
for each row execute function public.finca_owner_membership();

-- ---------------------------------------------------------------------
-- 2. DATOS INICIALES
-- ---------------------------------------------------------------------
insert into public.tipos_animales (nombre) values
    ('Vaca'), ('Toro'), ('Novillo'), ('Novilla'), ('Ternero'), ('Ternera')
on conflict (nombre) do nothing;

-- ---------------------------------------------------------------------
-- 3. SEGURIDAD (Row Level Security)
-- Cada usuario solo ve lo de las fincas donde es miembro.
-- OJO: tu backend FastAPI, si usa la service_role key o la conexión directa
-- de Postgres, se salta RLS. RLS protege el acceso directo desde el cliente
-- (anon key) y es la red de seguridad si algún día consultas desde el front.
-- ---------------------------------------------------------------------
alter table public.fincas         enable row level security;
alter table public.finca_miembros enable row level security;
alter table public.tipos_animales enable row level security;
alter table public.animales       enable row level security;
alter table public.eventos_animal enable row level security;

create or replace function public.es_miembro(p_finca_id bigint)
returns boolean language sql stable security definer set search_path = public as $$
    select exists (
        select 1 from public.finca_miembros
        where finca_id = p_finca_id and user_id = auth.uid()
    );
$$;

-- fincas
create policy "fincas: ver las mias"      on public.fincas for select
    using (public.es_miembro(id));
create policy "fincas: crear"             on public.fincas for insert
    with check (creada_por = auth.uid());
create policy "fincas: editar las mias"   on public.fincas for update
    using (public.es_miembro(id));
create policy "fincas: borrar propietario" on public.fincas for delete
    using (exists (select 1 from public.finca_miembros
                   where finca_id = id and user_id = auth.uid() and rol = 'propietario'));

-- finca_miembros
create policy "miembros: ver los de mis fincas" on public.finca_miembros for select
    using (public.es_miembro(finca_id));
create policy "miembros: gestiona el propietario" on public.finca_miembros for all
    using (exists (select 1 from public.finca_miembros m
                   where m.finca_id = finca_miembros.finca_id
                     and m.user_id = auth.uid() and m.rol = 'propietario'))
    with check (exists (select 1 from public.finca_miembros m
                   where m.finca_id = finca_miembros.finca_id
                     and m.user_id = auth.uid() and m.rol = 'propietario'));

-- tipos_animales: catálogo de lectura para usuarios autenticados
create policy "tipos: lectura" on public.tipos_animales for select
    to authenticated using (true);

-- animales
create policy "animales: ver los de mis fincas" on public.animales for select
    using (public.es_miembro(finca_id));
create policy "animales: crear en mis fincas"   on public.animales for insert
    with check (public.es_miembro(finca_id));
create policy "animales: editar en mis fincas"  on public.animales for update
    using (public.es_miembro(finca_id)) with check (public.es_miembro(finca_id));
create policy "animales: borrar en mis fincas"  on public.animales for delete
    using (public.es_miembro(finca_id));

-- eventos_animal
create policy "eventos: ver" on public.eventos_animal for select
    using (exists (select 1 from public.animales a
                   where a.id = animal_id and public.es_miembro(a.finca_id)));
create policy "eventos: crear" on public.eventos_animal for insert
    with check (exists (select 1 from public.animales a
                        where a.id = animal_id and public.es_miembro(a.finca_id)));
create policy "eventos: editar" on public.eventos_animal for update
    using (exists (select 1 from public.animales a
                   where a.id = animal_id and public.es_miembro(a.finca_id)));
create policy "eventos: borrar" on public.eventos_animal for delete
    using (exists (select 1 from public.animales a
                   where a.id = animal_id and public.es_miembro(a.finca_id)));

-- ---------------------------------------------------------------------
-- 4. BUCKET DE FOTOS (Supabase Storage)
-- Privado: las fotos se muestran con URLs firmadas que expiran.
-- Convención de ruta:  {finca_id}/{animal_id}/{archivo}
-- Límite 5 MB, solo imágenes.
-- ---------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'fotos-animales',
    'fotos-animales',
    false,
    5242880,
    array['image/jpeg','image/png','image/webp']
)
on conflict (id) do nothing;

-- Políticas de Storage: solo miembros de la finca (primer segmento de la ruta)
create policy "fotos: ver de mis fincas" on storage.objects for select
    using (bucket_id = 'fotos-animales'
           and public.es_miembro(((storage.foldername(name))[1])::bigint));

create policy "fotos: subir a mis fincas" on storage.objects for insert
    with check (bucket_id = 'fotos-animales'
                and public.es_miembro(((storage.foldername(name))[1])::bigint));

create policy "fotos: reemplazar en mis fincas" on storage.objects for update
    using (bucket_id = 'fotos-animales'
           and public.es_miembro(((storage.foldername(name))[1])::bigint));

create policy "fotos: borrar de mis fincas" on storage.objects for delete
    using (bucket_id = 'fotos-animales'
           and public.es_miembro(((storage.foldername(name))[1])::bigint));