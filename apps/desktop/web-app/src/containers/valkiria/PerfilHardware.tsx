/**
 * Valkiria (F1, HU-04): perfil de hardware en Ajustes → Hardware. No existe en Jan.
 *
 * Muestra la RAM, la aceleración y el perfil detectados (RN-04.1), deja bajar de perfil y deshabilita
 * los perfiles que la RAM no permite con la explicación del requisito (RN-04.2, CA-04.2), y muestra
 * los modelos del catálogo recomendados para el perfil en uso (CA-04.1).
 */
import { invoke } from '@tauri-apps/api/core'
import { useEffect, useState } from 'react'
import { Card, CardItem } from '@/containers/Card'
import { useTranslation } from '@/i18n/react-i18next-compat'

export type Perfil = 'estandar' | 'avanzado'

type Modelo = { id: string; nombre: string; rol: string; ram_gb: number }

export type EstadoPerfil = {
  ram_gb: number
  so: string
  arch: string
  acelerador: 'metal' | 'cuda' | 'vulkan' | 'cpu'
  perfil: Perfil
  perfil_maximo: Perfil
  aviso_rendimiento: boolean
  opciones: { perfil: Perfil; disponible: boolean; motivo: string | null }[]
  recomendacion: { principal: Modelo | null; router: Modelo | null }
}

export type PerfilApi = {
  leer: () => Promise<EstadoPerfil>
  elegir: (perfil: Perfil) => Promise<EstadoPerfil>
}

const tauriPerfilApi: PerfilApi = {
  leer: () => invoke<EstadoPerfil>('valkiria_perfil_hardware'),
  elegir: (perfil) =>
    invoke<EstadoPerfil>('valkiria_elegir_perfil', { perfil }),
}

const RAM_MINIMA: Record<Perfil, number> = { estandar: 0, avanzado: 32 }
const ACELERADOR: Record<EstadoPerfil['acelerador'], string> = {
  metal: 'Metal',
  cuda: 'CUDA',
  vulkan: 'Vulkan',
  cpu: 'CPU',
}

export function PerfilHardware({ api = tauriPerfilApi }: { api?: PerfilApi }) {
  const { t } = useTranslation()
  const [estado, setEstado] = useState<EstadoPerfil | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let vivo = true
    api
      .leer()
      .then((e) => vivo && setEstado(e))
      .catch((e) => console.error('Valkiria: perfil de hardware', e))
    return () => {
      vivo = false
    }
  }, [api])

  if (!estado) return null

  const nombre = (p: Perfil) => t(`settings:hardware.valkiria.${p}`)
  const elegir = (p: Perfil) => {
    setError(null)
    api
      .elegir(p)
      .then(setEstado)
      .catch((e) => setError(String(e)))
  }
  const modelo = (m: Modelo | null) =>
    m
      ? `${m.nombre || m.id} · ${m.ram_gb} GB`
      : t('settings:hardware.valkiria.pendiente')

  return (
    <Card title={t('settings:hardware.valkiria.titulo')}>
      <CardItem
        title={t('settings:hardware.valkiria.ram')}
        actions={<span className="text-foreground">{estado.ram_gb} GB</span>}
      />
      <CardItem
        title={t('settings:hardware.valkiria.acelerador')}
        actions={
          <span className="text-foreground">
            {ACELERADOR[estado.acelerador]}
          </span>
        }
      />
      <CardItem
        title={t('settings:hardware.valkiria.perfil')}
        description={
          estado.aviso_rendimiento ? (
            <span role="alert">{t('settings:hardware.valkiria.aviso')}</span>
          ) : undefined
        }
        column
        actions={
          <div role="radiogroup" className="flex flex-col gap-2 mt-2">
            {estado.opciones.map((o) => (
              <label
                key={o.perfil}
                className={
                  o.disponible
                    ? 'cursor-pointer'
                    : 'opacity-60 cursor-not-allowed'
                }
              >
                <span className="flex items-center gap-2 text-foreground">
                  <input
                    type="radio"
                    name="valkiria-perfil"
                    value={o.perfil}
                    checked={estado.perfil === o.perfil}
                    disabled={!o.disponible}
                    aria-describedby={
                      o.disponible ? undefined : `motivo-${o.perfil}`
                    }
                    onChange={() => o.disponible && elegir(o.perfil)}
                  />
                  {nombre(o.perfil)}
                </span>
                {!o.disponible && (
                  <span
                    id={`motivo-${o.perfil}`}
                    className="block ml-6 text-xs"
                  >
                    {t('settings:hardware.valkiria.requiereRam', {
                      perfil: nombre(o.perfil),
                      gb: RAM_MINIMA[o.perfil],
                      ram: estado.ram_gb,
                    })}
                  </span>
                )}
              </label>
            ))}
            {error && (
              <span role="alert" className="text-destructive text-xs">
                {error}
              </span>
            )}
          </div>
        }
      />
      <CardItem
        title={t('settings:hardware.valkiria.principal')}
        actions={
          <span className="text-foreground" data-testid="recomendado-principal">
            {modelo(estado.recomendacion.principal)}
          </span>
        }
      />
      <CardItem
        title={t('settings:hardware.valkiria.router')}
        actions={
          <span className="text-foreground" data-testid="recomendado-router">
            {modelo(estado.recomendacion.router)}
          </span>
        }
      />
    </Card>
  )
}
