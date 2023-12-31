let pyScript

onmessage = (event) => {
  const { eventType } = event.data
  switch (eventType) {
    case 'initialise':
      initialise().then(() => {
        self.postMessage({ eventType: 'initialiseDone' })
      })
      break

    case 'firstRunCycle':
      pyScript = self.pyodide.runPython(`port.start(${event.data.sessionId})`)
      runCycle(null)
      break

    case 'nextRunCycle':
      const { response } = event.data
      unwrap(response).then((userInput) => {
        runCycle(userInput)
      })
      break

    default:
      console.log('[ProcessingWorker] Received unsupported event: ', eventType)
  }
}

function runCycle(payload) {
  console.log('[ProcessingWorker] runCycle ' + JSON.stringify(payload))
  try {
    scriptEvent = pyScript.send(payload)
    self.postMessage({
      eventType: 'runCycleDone',
      scriptEvent: scriptEvent.toJs({
        create_proxies: false,
        dict_converter: Object.fromEntries
      })
    })
  } catch (error) {
    self.postMessage({
      eventType: 'runCycleDone',
      scriptEvent: generateErrorMessage(error.toString())
    })
  }
}

function unwrap(response) {
  console.log('[ProcessingWorker] unwrap response: ' + JSON.stringify(response.payload))
  return new Promise((resolve) => {
    switch (response.payload.__type__) {
      case 'PayloadFile':
        copyFileToPyFS(response.payload.value, resolve)
        break

      default:
        resolve(response.payload)
    }
  })
}

var fileCounter = 0

function copyFileToPyFS(file, resolve) {
  directoryName = `/file-input-${fileCounter++}`
  self.pyodide.FS.mkdir(directoryName)
  self.pyodide.FS.mount(
    self.pyodide.FS.filesystems.WORKERFS,
    {
      files: [file]
    },
    directoryName
  )
  console.log(file.name)
  resolve({ __type__: 'PayloadString', value: directoryName + '/' + file.name })
}
function initialise() {
  console.log('[ProcessingWorker] initialise')
  return startPyodide()
    .then((pyodide) => {
      self.pyodide = pyodide
      return loadPackages()
    })
    .then(() => {
      return installPortPackage()
    })
}

function startPyodide() {
  importScripts('https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js')

  console.log('[ProcessingWorker] loading Pyodide')
  return loadPyodide({
    indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/'
  })
}

function loadPackages() {
  console.log('[ProcessingWorker] loading packages')
  return self.pyodide.loadPackage(['micropip', 'numpy', 'pandas'])
}

function installPortPackage() {
  console.log('[ProcessingWorker] load port package')
  return self.pyodide.runPythonAsync(`
    import micropip
    await micropip.install("https://files.pythonhosted.org/packages/32/4d/aaf7eff5deb402fd9a24a1449a8119f00d74ae9c2efa79f8ef9994261fc2/pytz-2023.3.post1-py2.py3-none-any.whl")
    await micropip.install("../../port-0.0.0-py3-none-any.whl", deps=False)
    import port
  `)
}

function generateErrorMessage(stacktrace) {
  return {
    __type__: 'CommandUIRender',
    page: {
      __type__: 'PropsUIPageError',
      stacktrace: stacktrace
    }
  }
}
