#!/bin/sh

PROJECT_DIR=$(dirname "$(dirname "$(readlink -f "$0")")")
SCREEN_SIZE=${SCREEN_SIZE:-1920x1080}
XDISPLAY=${XDISPLAY:-:1}
if [[ -z "${PYTHON}" ]]; then
  if [[ -f "${PROJECT_DIR}/venv/bin/python" ]]; then
    PYTHON="${PROJECT_DIR}/venv/bin/python"
  else
    PYTHON=python
  fi
fi

nested() {
  env DISPLAY=${XDISPLAY} PYTHON="${PYTHON}" "$@"
}

Xephyr +extension RANDR -screen ${SCREEN_SIZE} ${XDISPLAY} -ac &
XEPHYR_PID=$!
(
  sleep 1
  nested "${PYTHON}" "${PROJECT_DIR}/bin/qtile" -c "${PROJECT_DIR}/docs/screenshots/config.py" &
  QTILE_PID=$!

  sleep 1
  case $1 in
    -i|--interactive)
      nested xterm
    ;;
    *)
      nested xterm -e "${PYTHON}" "${PROJECT_DIR}/docs/screenshots/take_all.py" "$@"
      sleep 1
      nested xterm -e qtile-cmd -o cmd -f shutdown
    ;;
  esac

  wait $QTILE_PID
  kill $XEPHYR_PID
)
