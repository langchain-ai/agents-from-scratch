# Guía de Instalación de WSL (Windows Subsystem for Linux)

## 📋 Tabla de Contenidos
- [¿Qué es WSL?](#qué-es-wsl)
- [Requisitos del Sistema](#requisitos-del-sistema)
- [Método 1: Instalación Automática (Recomendado)](#método-1-instalación-automática-recomendado)
- [Método 2: Instalación Manual](#método-2-instalación-manual)
- [Configuración Inicial](#configuración-inicial)
- [Comandos Útiles de WSL](#comandos-útiles-de-wsl)
- [Solución de Problemas](#solución-de-problemas)
- [Recursos Adicionales](#recursos-adicionales)

## ¿Qué es WSL?

WSL (Windows Subsystem for Linux) es una capa de compatibilidad desarrollada por Microsoft que permite ejecutar un entorno Linux dentro de Windows de forma nativa. Con WSL puedes:

- Ejecutar herramientas de línea de comandos de Linux
- Desarrollar aplicaciones multiplataforma
- Usar un terminal bash completo
- Instalar y usar paquetes de Linux

## Requisitos del Sistema

### Para WSL 2 (Recomendado):
- Windows 10 versión 1903 o superior (Build 18362 o superior)
- Windows 11 (cualquier versión)
- Arquitectura x64 o ARM64
- Al menos 4 GB de RAM
- Virtualización habilitada en BIOS/UEFI

### Para WSL 1:
- Windows 10 versión 1607 o superior
- Arquitectura x64

## Método 1: Instalación Automática (Recomendado)

Este es el método más sencillo para usuarios de Windows 10 versión 2004 o superior y Windows 11.

### Paso 1: Abrir PowerShell como Administrador
1. Presiona `Win + X`
2. Selecciona "Windows PowerShell (Administrador)" o "Terminal (Administrador)"

### Paso 2: Ejecutar el comando de instalación
```powershell
wsl --install
```

Este comando automáticamente:
- Habilita las características necesarias de Windows
- Descarga e instala el kernel de Linux más reciente
- Establece WSL 2 como versión predeterminada
- Instala Ubuntu como distribución predeterminada

### Paso 3: Reiniciar el sistema
Reinicia tu computadora cuando se te solicite.

### Paso 4: Configurar tu distribución
Al reiniciar, se abrirá automáticamente la terminal de Ubuntu. Sigue las instrucciones para:
- Crear un nombre de usuario
- Establecer una contraseña

## Método 2: Instalación Manual

Si el método automático no funciona o prefieres tener más control sobre el proceso:

### Paso 1: Habilitar WSL
Abre PowerShell como administrador y ejecuta:
```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

### Paso 2: Habilitar la Plataforma de Máquina Virtual
```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

### Paso 3: Reiniciar el sistema
Reinicia tu computadora.

### Paso 4: Descargar el paquete de actualización del kernel de Linux
1. Descarga el [paquete de actualización del kernel de WSL2](https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi)
2. Ejecuta el archivo descargado e instálalo

### Paso 5: Establecer WSL 2 como versión predeterminada
```powershell
wsl --set-default-version 2
```

### Paso 6: Instalar una distribución de Linux
1. Abre Microsoft Store
2. Busca tu distribución preferida (Ubuntu, Debian, openSUSE, etc.)
3. Instala la distribución elegida
4. Lanza la aplicación y completa la configuración inicial

## Configuración Inicial

### Actualizar el sistema
Una vez dentro de tu distribución Linux, actualiza los paquetes:
```bash
sudo apt update && sudo apt upgrade -y
```

### Instalar herramientas básicas
```bash
# Herramientas de desarrollo
sudo apt install build-essential curl git wget -y

# Editor de texto (opcional)
sudo apt install nano vim -y
```

### Configurar Git (opcional)
```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu.email@ejemplo.com"
```

## Comandos Útiles de WSL

### Comandos básicos:
```powershell
# Listar distribuciones instaladas
wsl -l -v

# Iniciar WSL
wsl

# Iniciar una distribución específica
wsl -d Ubuntu

# Detener todas las distribuciones
wsl --shutdown

# Detener una distribución específica
wsl -t Ubuntu

# Establecer distribución predeterminada
wsl --set-default Ubuntu

# Actualizar WSL
wsl --update
```

### Acceso a archivos:
- **Desde Windows a WSL**: `\\wsl$\Ubuntu\home\usuario`
- **Desde WSL a Windows**: `/mnt/c/Users/TuUsuario`

## Solución de Problemas

### Error: "La operación solicitada requiere elevación"
- Ejecuta PowerShell como administrador

### Error: "WSL 2 requiere una actualización de su componente kernel"
- Descarga e instala el paquete de actualización del kernel WSL2

### Error: "Virtualización no está habilitada"
1. Reinicia y entra a BIOS/UEFI
2. Busca opciones de virtualización (Intel VT-x/AMD-V)
3. Habilita la virtualización
4. Guarda y reinicia

### La distribución no inicia:
```powershell
# Reiniciar WSL
wsl --shutdown
wsl

# Si persiste el problema, reiniciar la distribución
wsl --unregister Ubuntu
# Luego reinstalar desde Microsoft Store
```

### Problemas de rendimiento:
```powershell
# Asignar más memoria a WSL2 (crear/editar .wslconfig)
# En C:\Users\TuUsuario\.wslconfig
[wsl2]
memory=4GB
processors=2
```

## Recursos Adicionales

### Documentación oficial:
- [Documentación de Microsoft WSL](https://docs.microsoft.com/es-es/windows/wsl/)
- [Guía de instalación de WSL](https://docs.microsoft.com/es-es/windows/wsl/install)

### Distribuciones populares:
- **Ubuntu**: La más popular y fácil de usar
- **Debian**: Estable y minimalista
- **openSUSE**: Buena para usuarios avanzados
- **Kali Linux**: Para seguridad y pentesting

### Herramientas recomendadas:
- **Windows Terminal**: Terminal moderna y personalizable
- **Visual Studio Code**: Editor con excelente integración con WSL
- **Docker Desktop**: Para contenedores con soporte WSL2

## 🛠️ Integración con Visual Studio Code

Visual Studio Code ofrece una integración excepcional con WSL, permitiéndote desarrollar directamente en el entorno Linux desde Windows.

### Instalación de la extensión WSL

1. **Instalar Visual Studio Code** desde [code.visualstudio.com](https://code.visualstudio.com/)

2. **Instalar la extensión WSL:**
   - Abre VS Code
   - Ve a la pestaña de Extensiones (`Ctrl+Shift+X`)
   - Busca "WSL" y instala la extensión oficial de Microsoft

### Trabajando con WSL en VS Code

#### Método 1: Desde Windows
```powershell
# Navegar a tu proyecto y abrir en VS Code
cd \\wsl$\Ubuntu\home\usuario\mi-proyecto
code .
```

#### Método 2: Desde WSL Terminal
```bash
# Dentro de WSL, navegar a tu proyecto
cd ~/mi-proyecto
code .
```

#### Método 3: Comando directo
```powershell
# Abrir WSL directamente en VS Code
code --remote wsl+Ubuntu
```

### Configuración recomendada para desarrollo

#### Extensiones esenciales para WSL:
- **WSL**: Conexión con el subsistema Linux
- **Remote Development**: Suite completa para desarrollo remoto
- **Git History**: Visualización de historial de Git
- **GitLens**: Mejoras para Git
- **Prettier**: Formateo de código
- **ESLint**: Linting para JavaScript/TypeScript

#### Configuración del workspace:
```json
{
  "terminal.integrated.defaultProfile.linux": "bash",
  "terminal.integrated.profiles.linux": {
    "bash": {
      "path": "/bin/bash"
    }
  },
  "git.enabled": true,
  "git.path": "/usr/bin/git",
  "remote.WSL.fileWatcher.polling": true
}
```

### Flujo de trabajo típico para workshops

#### 1. Preparación del entorno de desarrollo:
```bash
# Crear directorio del proyecto
mkdir ~/workshop-agentes-ia
cd ~/workshop-agentes-ia

# Inicializar Git
git init

# Crear estructura básica
mkdir src tests docs
touch README.md requirements.txt

# Abrir en VS Code
code .
```

#### 2. Instalación de herramientas de desarrollo:
```bash
# Python y pip
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

# Node.js y npm (para proyectos web)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Herramientas adicionales
sudo apt install git curl wget build-essential -y
```

#### 3. Configuración de entorno virtual Python:
```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Características avanzadas de VS Code + WSL

#### Debug integrado:
- Configurar breakpoints directamente en VS Code
- Debug de aplicaciones Python, Node.js, etc.
- Variables y call stack en tiempo real

#### Terminal integrada:
- Terminal bash nativa de Linux
- Múltiples terminales simultáneas
- Integración con Git

#### Explorador de archivos:
- Acceso directo a archivos Linux
- Sincronización automática
- Arrastrar y soltar entre Windows y WSL

#### Extensiones específicas para WSL:
```bash
# Instalar extensiones desde terminal
code --install-extension ms-python.python
code --install-extension ms-vscode.vscode-json
code --install-extension bradlc.vscode-tailwindcss
```

### Consejos para workshops y desarrollo colaborativo

#### Compartir configuración del proyecto:
Crear `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true,
  "files.autoSave": "afterDelay",
  "git.autofetch": true
}
```

#### Configurar tareas automatizadas:
Crear `.vscode/tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Install Dependencies",
      "type": "shell",
      "command": "pip install -r requirements.txt",
      "group": "build"
    },
    {
      "label": "Run Tests",
      "type": "shell",
      "command": "python -m pytest",
      "group": "test"
    }
  ]
}
```

#### Configuración de debug:
Crear `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

### Solución de problemas con VS Code + WSL

#### VS Code no detecta WSL:
```powershell
# Reinstalar la extensión WSL
code --uninstall-extension ms-vscode-remote.remote-wsl
code --install-extension ms-vscode-remote.remote-wsl
```

#### Problemas de rendimiento:
```bash
# Configurar watchman para mejor rendimiento
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### Git no funciona correctamente:
```bash
# Configurar Git en WSL
git config --global user.name "Tu Nombre"
git config --global user.email "tu.email@ejemplo.com"
git config --global init.defaultBranch main
```

## 🎉 ¡Listo!

Ahora tienes WSL instalado y configurado en tu sistema Windows. Puedes empezar a usar herramientas de Linux, desarrollar aplicaciones, y disfrutar de lo mejor de ambos mundos.

### Próximos pasos recomendados:
1. Instalar Windows Terminal para una mejor experiencia
2. Configurar tu entorno de desarrollo favorito
3. Explorar la integración con Visual Studio Code
4. Instalar Docker Desktop con soporte WSL2

---

**¿Necesitas ayuda adicional?** Consulta la documentación oficial o busca en la comunidad de desarrolladores de Microsoft. 