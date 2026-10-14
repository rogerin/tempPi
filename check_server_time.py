#!/usr/bin/env python3
"""Read-only clock diagnostic for Raspberry Pi OS; no external dependencies."""
import subprocess
from datetime import datetime, timezone


def check_server_time() -> bool:
    """Report systemd's synchronization status; never change the system clock."""
    now = datetime.now(timezone.utc)
    print(f"🕒 Data/hora local do servidor: {now.astimezone().isoformat(timespec='seconds')}")
    print(f"🕒 Data/hora UTC: {now.isoformat(timespec='seconds')}")
    try:
        result = subprocess.run(
            ['timedatectl', 'show', '--property=NTPSynchronized', '--value'],
            capture_output=True, text=True, check=True, timeout=5,
        )
        status = result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        status = None

    if status == 'yes':
        print('✅ Relógio sincronizado segundo o sistema (NTP).')
        return True
    if status == 'no':
        print('⚠️ Relógio não sincronizado. A data/hora dos registros pode estar incorreta.')
    else:
        print('⚠️ Não foi possível confirmar a sincronização do relógio neste sistema.')
    print('   No Raspberry Pi, confira a rede, a data e o fuso com: timedatectl status')
    print('   Para habilitar a sincronização: sudo timedatectl set-ntp true')
    print('   A inicialização continuará; esta checagem não altera a hora do servidor.')
    return False


if __name__ == '__main__':
    raise SystemExit(0 if check_server_time() else 1)
