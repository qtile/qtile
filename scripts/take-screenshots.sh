#!/bin/sh

PROJECT_DIR=$(dirname "$(dirname "$(readlink -f "$0")")")
SCREEN_SIZE=${SCREEN_SIZE:-1920x1080}
XDISPLAY=${XDISPLAY:-:1}
LOG_PATH=${PROJECT_DIR}/docs/screenshots/screenshots.log
if [[ -z "${PYTHON}" ]]; then
  if [[ -f "${PROJECT_DIR}/venv/bin/python" ]]; then
    PYTHON="${PROJECT_DIR}/venv/bin/python"
  else
    PYTHON=python
  fi
fi

nested() {
  env DISPLAY=${XDISPLAY} PYTHON="${PYTHON}" LOG_PATH="${LOG_PATH}" "$@"
}

rm "${LOG_PATH}" &>/dev/null
touch "${LOG_PATH}"

Xephyr +extension RANDR -screen ${SCREEN_SIZE} ${XDISPLAY} -ac &>/dev/null &
XEPHYR_PID=$!
(
  sleep 1
  nested "${PYTHON}" "${PROJECT_DIR}/bin/qtile" -l CRITICAL -c "${PROJECT_DIR}/docs/screenshots/config.py" &
  QTILE_PID=$!

  sleep 1
  case $1 in
    -i|--interactive)
      nested xterm
    ;;
    *)
      nested xterm -e "${PYTHON}" "${PROJECT_DIR}/docs/screenshots/take_all.py" "$@" &
      XTERM_PID=$!

      tail -f "${LOG_PATH}" &

      wait $XTERM_PID
      sleep 1
      nested xterm -e qtile-cmd -o cmd -f shutdown
    ;;
  esac

  wait $QTILE_PID
  kill $XEPHYR_PID
)
