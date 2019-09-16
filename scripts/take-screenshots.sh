#!/bin/sh

PROJECT_DIR=$(dirname "$(dirname "$(readlink -f "$0")")")
SCREEN_SIZE=${SCREEN_SIZE:-800x600}
XDISPLAY=${XDISPLAY:-:1}
if [[ -z $PYTHON ]]; then
    PYTHON=python
fi

Xephyr +extension RANDR -screen ${SCREEN_SIZE} ${XDISPLAY} -ac &
XEPHYR_PID=$!
(
  sleep 1
  env DISPLAY=${XDISPLAY} ${PYTHON} "${PROJECT_DIR}/bin/qtile" -c "${PROJECT_DIR}/docs/screenshots/config.py" &
  QTILE_PID=$!

  sleep 1
  case $1 in
    -i|--interactive)
      env DISPLAY=${XDISPLAY} xterm
    ;;
    *)
      env DISPLAY=${XDISPLAY} xterm -e "${PYTHON}" "${PROJECT_DIR}/docs/screenshots/take_all.py" "$@"
      sleep 1
      env DISPLAY=${XDISPLAY} xterm -e qtile-cmd -o cmd -f shutdown
    ;;
  esac

  wait $QTILE_PID
  kill $XEPHYR_PID
)
