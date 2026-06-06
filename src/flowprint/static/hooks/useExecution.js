import { useRef } from "react";
import { RunSession } from "../api/ws.js";
import { useStore } from "../store/context.js";
import { A } from "../store/actions.js";

export function useExecution() {
  const { dispatch } = useStore();
  const sessionRef = useRef(null);

  function run(graph, args) {
    dispatch({ type: A.EXECUTION_STARTED });
    sessionRef.current = new RunSession(graph, args, {
      onEvent: ev  => dispatch({ type: A.EXECUTION_EVENT, payload: ev }),
      onDone:  ()  => dispatch({ type: A.EXECUTION_DONE }),
    });
    sessionRef.current.start();
  }

  function cancel() {
    sessionRef.current?.cancel();
    dispatch({ type: A.EXECUTION_DONE });
  }

  return { run, cancel };
}
