classDiagram
    class PolyCallClient {
        -options: ClientOptions
        -socket: Socket
        -stateMachine: StateMachine
        -router: Router
        +connect(port: number, host: string)
        +disconnect()
        +sendCommand(path: string, data: any)
    }

    class Router {
        -routes: Map~string, RouteHandler~
        +addRoute(path: string, handler: RouteHandler)
        +handleRequest(path: string, data: any)
        +mapStateToEndpoint(state: State)
    }

    class StateMachine {
        -currentState: State
        -states: Map~string, State~
        -transitions: Map~string, Transition~
        +addState(name: string)
        +addTransition(from: string, to: string)
        +executeTransition(name: string)
    }

    class State {
        -name: string
        -isLocked: boolean
        -handlers: Map~string, StateHandler~
        +getEndpoint(): string
        +lock()
        +unlock()
    }

    class NetworkEndpoint {
        -protocol: Protocol
        -port: number
        -address: string
        +bind()
        +listen()
        +send(data: any)
    }

    class ProtocolHandler {
        -version: number
        -checksumAlgorithm: string
        +createHeader(type: MessageType)
        +verifyMessage(data: Buffer)
        +handleHandshake()
    }

    PolyCallClient --> Router
    PolyCallClient --> StateMachine
    PolyCallClient --> NetworkEndpoint
    Router --> State
    StateMachine --> State
    PolyCallClient --> ProtocolHandler
    NetworkEndpoint --> ProtocolHandler