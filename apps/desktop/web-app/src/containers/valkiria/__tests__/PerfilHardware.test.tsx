import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import {
  PerfilHardware,
  type EstadoPerfil,
  type Perfil,
  type PerfilApi,
} from '../PerfilHardware'

vi.mock('@/i18n/react-i18next-compat', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts ? `${key} ${JSON.stringify(opts)}` : key,
  }),
}))

const router = {
  id: 'qwen3-0.6b-q8_0',
  nombre: 'Qwen3 0.6B',
  rol: 'router',
  ram_gb: 1,
}

function equipo(ram: number, perfil?: Perfil): EstadoPerfil {
  const maximo: Perfil = ram >= 32 ? 'avanzado' : 'estandar'
  return {
    ram_gb: ram,
    so: 'macos',
    arch: 'aarch64',
    acelerador: 'metal',
    perfil: perfil ?? maximo,
    perfil_maximo: maximo,
    aviso_rendimiento: ram < 16,
    opciones: [
      { perfil: 'estandar', disponible: true, motivo: null },
      {
        perfil: 'avanzado',
        disponible: ram >= 32,
        motivo: ram >= 32 ? null : 'requiere 32 GB',
      },
    ],
    recomendacion: {
      principal:
        ram >= 32
          ? { id: 'grande', nombre: 'Grande', rol: 'principal', ram_gb: 20 }
          : null,
      router,
    },
  }
}

function api(
  inicial: EstadoPerfil
): PerfilApi & { elegir: ReturnType<typeof vi.fn> } {
  return {
    leer: vi.fn().mockResolvedValue(inicial),
    elegir: vi.fn((p: Perfil) => Promise.resolve(equipo(inicial.ram_gb, p))),
  }
}

describe('PerfilHardware (HU-04)', () => {
  it('CA-04.1: con 32 GB y Metal el perfil es Avanzado y recomienda su modelo principal', async () => {
    render(<PerfilHardware api={api(equipo(32))} />)
    const avanzado = await screen.findByRole('radio', { name: /avanzado/i })
    expect(avanzado).toBeChecked()
    expect(avanzado).toBeEnabled()
    expect(screen.getByText('32 GB')).toBeInTheDocument()
    expect(screen.getByText('Metal')).toBeInTheDocument()
    expect(screen.getByTestId('recomendado-principal')).toHaveTextContent(
      'Grande · 20 GB'
    )
    expect(screen.getByTestId('recomendado-router')).toHaveTextContent(
      'Qwen3 0.6B · 1 GB'
    )
  })

  it('CA-04.2: con 16 GB la opción Avanzado está deshabilitada con el requisito de RAM', async () => {
    const a = api(equipo(16))
    render(<PerfilHardware api={a} />)
    const avanzado = await screen.findByRole('radio', { name: /avanzado/i })
    expect(avanzado).toBeDisabled()
    expect(screen.getByRole('radio', { name: /estandar/i })).toBeChecked()
    const motivo = document.getElementById('motivo-avanzado')
    expect(motivo).toHaveTextContent('settings:hardware.valkiria.requiereRam')
    expect(motivo).toHaveTextContent('"gb":32')
    expect(motivo).toHaveTextContent('"ram":16')
    expect(avanzado).toHaveAttribute('aria-describedby', 'motivo-avanzado')
    fireEvent.click(avanzado)
    expect(a.elegir).not.toHaveBeenCalled()
  })

  it('RN-04.2: en un equipo de 32 GB se puede bajar a Estándar', async () => {
    const a = api(equipo(32))
    render(<PerfilHardware api={a} />)
    fireEvent.click(await screen.findByRole('radio', { name: /estandar/i }))
    expect(a.elegir).toHaveBeenCalledWith('estandar')
    await waitFor(() =>
      expect(screen.getByRole('radio', { name: /estandar/i })).toBeChecked()
    )
  })

  it('RN-04.1: con menos de 16 GB avisa del rendimiento limitado', async () => {
    render(<PerfilHardware api={api(equipo(8))} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'settings:hardware.valkiria.aviso'
    )
  })

  it('sin modelo principal en el catálogo lo indica como pendiente', async () => {
    render(<PerfilHardware api={api(equipo(16))} />)
    expect(
      await screen.findByTestId('recomendado-principal')
    ).toHaveTextContent('settings:hardware.valkiria.pendiente')
  })

  it('si el comando falla no muestra nada', async () => {
    const a: PerfilApi = {
      leer: vi.fn().mockRejectedValue(new Error('sin Tauri')),
      elegir: vi.fn(),
    }
    const err = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { container } = render(<PerfilHardware api={a} />)
    await waitFor(() => expect(err).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
    err.mockRestore()
  })
})
