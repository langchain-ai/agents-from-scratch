# 🚀 GitHub Codespaces - Entorno de Desarrollo en la Nube
*La mejor opción para el Workshop de Agentes Inteligentes*

## 📋 Tabla de Contenidos
- [¿Qué es GitHub Codespaces?](#qué-es-github-codespaces)
- [¿Por qué Codespaces es la mejor opción?](#por-qué-codespaces-es-la-mejor-opción)
- [Configuración Inicial](#configuración-inicial)
- [Crear tu primer Codespace](#crear-tu-primer-codespace)
- [Trabajando con Codespaces](#trabajando-con-codespaces)
- [Configuración para el Workshop](#configuración-para-el-workshop)
- [Mejores Prácticas](#mejores-prácticas)
- [Solución de Problemas](#solución-de-problemas)
- [Recursos Adicionales](#recursos-adicionales)

## ¿Qué es GitHub Codespaces?

GitHub Codespaces es un entorno de desarrollo instantáneo en la nube que te permite escribir, ejecutar y depurar código directamente desde tu navegador web. Es como tener Visual Studio Code completo corriendo en un servidor potente de GitHub.

### ✨ Características principales:
- **Entorno preconfigurado**: Sin instalaciones complejas
- **Acceso desde cualquier dispositivo**: Solo necesitas un navegador
- **Potencia de cómputo en la nube**: Máquinas virtuales de hasta 32 núcleos
- **Visual Studio Code completo**: Todas las extensiones y funcionalidades
- **Integración perfecta con GitHub**: Sincronización automática

## ¿Por qué Codespaces es la mejor opción?

### 🎯 **Para el Workshop de Agentes Inteligentes:**

#### ✅ **Ventajas principales:**
- **⚡ Configuración instantánea**: En 2 minutos tienes todo listo
- **🌐 Acceso universal**: Funciona en Windows, Mac, Linux, tablets
- **🔧 Entorno consistente**: Todos los participantes tienen el mismo setup
- **💾 Sin problemas de espacio**: Storage ilimitado en la nube
- **🚀 Alto rendimiento**: Procesadores potentes para IA y machine learning
- **🔄 Sincronización automática**: Cambios guardados en tiempo real
- **📱 Flexibilidad**: Puedes trabajar desde casa, oficina o cualquier lugar

#### ⚠️ **Comparado con alternativas:**

| Aspecto | GitHub Codespaces | WSL | Instalación Local |
|---------|-------------------|-----|-------------------|
| **Tiempo de setup** | 2 minutos | 30-60 minutos | 1-2 horas |
| **Compatibilidad** | 100% garantizada | Puede fallar | Depende del sistema |
| **Rendimiento** | Excelente | Variable | Depende del hardware |
| **Problemas técnicos** | Mínimos | Comunes | Muy comunes |
| **Soporte multiplataforma** | Perfecto | Solo Windows | Limitado |

## Configuración Inicial

### Paso 1: Crear cuenta en GitHub (si no tienes)

1. Ve a [github.com](https://github.com)
2. Haz clic en "Sign up"
3. Completa el registro con tu email corporativo o personal
4. Verifica tu email

### Paso 2: Verificar acceso a Codespaces

1. Inicia sesión en GitHub
2. Ve a tu perfil → Settings → Codespaces
3. Verifica que tienes acceso (todos los usuarios de GitHub tienen acceso gratuito)

### Paso 3: Configurar preferencias básicas

En GitHub Settings → Codespaces:
- **Editor**: Visual Studio Code (recomendado)
- **Región**: US East (mejor para Latinoamérica)
- **Timeout**: 30 minutos
- **Retain codespaces**: 30 días

## Crear tu primer Codespace

### Método 1: Desde el repositorio del workshop

1. **Ir al repositorio oficial:**
   ```
   https://github.com/yemoncada/agents-from-scratch
   ```

2. **Crear Codespace:**
   - Haz clic en el botón verde "Code"
   - Selecciona la pestaña "Codespaces"
   - Haz clic en "Create codespace on main"

3. **Configuración de máquina:**
   - **Para el workshop**: 4-core, 16GB RAM (recomendado)
   - **Opción básica**: 2-core, 8GB RAM (suficiente)

### Método 2: Desde tu fork del repositorio

1. **Fork el repositorio:**
   - Ve al repositorio del workshop
   - Haz clic en "Fork" (esquina superior derecha)
   - Crea el fork en tu cuenta

2. **Crear Codespace desde tu fork:**
   - Ve a tu fork
   - Sigue los pasos del Método 1

### Método 3: Usando plantilla

1. **Usar como template:**
   - Botón "Use this template"
   - "Create a new repository"
   - Nombra tu repositorio: `mi-workshop-agentes`
   - Crear Codespace desde tu nuevo repo

## Trabajando con Codespaces

### Interface principal

Tu Codespace tendrá:
- **Visual Studio Code completo** en el navegador
- **Terminal integrada** con bash
- **Explorador de archivos** con todos los archivos del proyecto
- **Panel de extensiones** para instalar herramientas adicionales

### Comandos esenciales

#### Gestión de Codespaces:
```bash
# Ver todos tus codespaces
gh codespace list

# Conectar a un codespace específico
gh codespace ssh -c CODESPACE_NAME

# Parar un codespace
gh codespace stop -c CODESPACE_NAME

# Eliminar un codespace
gh codespace delete -c CODESPACE_NAME
```

#### Desarrollo básico:
```bash
# Verificar Python
python3 --version

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar scripts
python src/main.py

# Activar entorno virtual (si es necesario)
source venv/bin/activate
```

### Extensiones recomendadas para el workshop

Tu Codespace incluirá automáticamente:
- **Python**: IntelliSense, debugging, linting
- **Jupyter**: Para notebooks interactivos
- **Git**: Control de versiones integrado
- **Docker**: Para contenedores (si necesario)

Extensiones adicionales útiles:
```bash
# Instalar extensiones desde terminal
code --install-extension ms-python.python
code --install-extension ms-toolsai.jupyter
code --install-extension ms-vscode.vscode-json
```

## Configuración para el Workshop

### Estructura de proyecto recomendada

```
mi-workshop-agentes/
├── .devcontainer/          # Configuración de Codespaces
├── src/                    # Código fuente
│   ├── agents/            # Agentes inteligentes
│   ├── tools/             # Herramientas personalizadas
│   └── utils/             # Utilidades
├── notebooks/             # Jupyter notebooks
├── data/                  # Datasets
├── tests/                 # Pruebas
├── requirements.txt       # Dependencias Python
├── .env.example          # Variables de entorno
└── README.md             # Documentación
```

### Configuración automática (.devcontainer)

Crea `.devcontainer/devcontainer.json`:
```json
{
  "name": "Workshop Agentes IA",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/git:1": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-toolsai.jupyter",
        "ms-python.black-formatter",
        "ms-python.flake8",
        "ms-vscode.vscode-json"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.formatting.provider": "black",
        "editor.formatOnSave": true
      }
    }
  },
  "postCreateCommand": "pip install -r requirements.txt",
  "forwardPorts": [8000, 8080, 3000],
  "portsAttributes": {
    "8000": {
      "label": "Streamlit App",
      "onAutoForward": "notify"
    }
  }
}
```

### Variables de entorno para el workshop

Crea `.env` en tu Codespace:
```bash
# APIs requeridas para el workshop
OPENAI_API_KEY=tu_openai_api_key
LANGCHAIN_API_KEY=tu_langsmith_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=workshop-agentes-ia

# Configuración adicional
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Configurar APIs necesarias

#### 1. OpenAI API Key:
```bash
# Configurar en el terminal del Codespace
export OPENAI_API_KEY="tu-api-key-aqui"
echo 'export OPENAI_API_KEY="tu-api-key-aqui"' >> ~/.bashrc
```

#### 2. LangSmith (para monitoreo):
```bash
export LANGCHAIN_API_KEY="tu-langsmith-key"
export LANGCHAIN_TRACING_V2=true
echo 'export LANGCHAIN_API_KEY="tu-langsmith-key"' >> ~/.bashrc
echo 'export LANGCHAIN_TRACING_V2=true' >> ~/.bashrc
```

## Mejores Prácticas

### Durante el workshop:

#### 🔄 **Guardar trabajo frecuentemente:**
```bash
# Auto-guardar está habilitado, pero también puedes:
git add .
git commit -m "Progreso del workshop: módulo 1 completado"
git push
```

#### 📊 **Gestionar recursos:**
- **Pausa tu Codespace** cuando no lo uses (se para automáticamente después de 30 min)
- **Usa máquina apropiada**: 4-core para workshop, 2-core para práctica
- **Cierra terminales innecesarias** para optimizar memoria

#### 🔐 **Seguridad:**
- **Nunca subas API keys** al repositorio público
- **Usa archivos .env** para configuración sensible
- **Agrega .env a .gitignore**

### Colaboración durante el workshop:

#### 👥 **Trabajo en equipo:**
```bash
# Compartir tu Codespace (solo lectura)
gh codespace ports visibility 8000:public -c $CODESPACE_NAME

# Crear repositorio colaborativo
gh repo create workshop-equipo-1 --public --clone
```

#### 📝 **Documentar progreso:**
- Usa Jupyter notebooks para experimentar
- Documenta hallazgos en markdown
- Comparte snippets útiles con el equipo

## Solución de Problemas

### Problemas comunes y soluciones:

#### ❌ Codespace no inicia:
```bash
# Verificar status
gh codespace list

# Recrear codespace
gh codespace delete -c CODESPACE_NAME
# Luego crear uno nuevo desde GitHub
```

#### ❌ Dependencias no se instalan:
```bash
# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias manualmente
pip install -r requirements.txt --force-reinstall
```

#### ❌ Problemas con extensiones:
```bash
# Reinstalar extensión Python
code --uninstall-extension ms-python.python
code --install-extension ms-python.python
```

#### ❌ Puerto no accesible:
```bash
# Verificar puertos
gh codespace ports -c $CODESPACE_NAME

# Hacer puerto público
gh codespace ports visibility 8000:public -c $CODESPACE_NAME
```

### Limpieza y mantenimiento:

```bash
# Ver uso de Codespaces
gh codespace list

# Eliminar codespaces viejos
gh codespace delete -c CODESPACE_NAME

# Limpiar caché
pip cache purge
```

## Recursos Adicionales

### Documentación oficial:
- [GitHub Codespaces Docs](https://docs.github.com/en/codespaces)
- [Configuración de devcontainer](https://containers.dev/)
- [VS Code en Codespaces](https://code.visualstudio.com/docs/remote/codespaces)

### Tutoriales específicos:
- [Codespaces para Python](https://docs.github.com/en/codespaces/getting-started/quickstart-for-python)
- [Configuración avanzada](https://docs.github.com/en/codespaces/customizing-your-codespace)

### Comunidad y soporte:
- [GitHub Community](https://github.community/c/codespaces)
- [VS Code Discord](https://aka.ms/vscode-discord)

### Precios y límites:
- **Usuarios personales**: 120 core-hours gratis/mes
- **GitHub Pro**: 180 core-hours gratis/mes
- **Organizaciones**: Facturación por uso

## 🎉 ¡Estás listo para el Workshop!

Con GitHub Codespaces tienes:
- ✅ **Entorno profesional** sin instalaciones
- ✅ **Acceso desde cualquier dispositivo**
- ✅ **Rendimiento garantizado**
- ✅ **Sincronización automática**
- ✅ **Soporte técnico de GitHub**

### Checklist final:
- [ ] Cuenta de GitHub creada y verificada
- [ ] Codespace creado desde el repositorio del workshop
- [ ] API keys configuradas (OpenAI, LangSmith)
- [ ] Dependencias instaladas correctamente
- [ ] Primer script de prueba ejecutado exitosamente

---

**¿Tienes dudas?** Recuerda que durante el workshop tendrás soporte completo para cualquier problema técnico. GitHub Codespaces garantiza que todos los participantes tengan una experiencia uniforme y sin problemas.

**¡Nos vemos en el workshop!** 🚀 