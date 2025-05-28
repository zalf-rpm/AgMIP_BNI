set PATH_TO_MONICA_BIN_DIR=C:\Users\escueta\MONICA\monica_win64_3.6.30\bin
set MONICA_PARAMETERS=C:\Users\escueta\PycharmProjects\AgMIP_BNI\data\monica-parameters

START "ZMQ_IN_PROXY" /MIN %PATH_TO_MONICA_BIN_DIR%\monica-zmq-proxy -pps -f 6666 -b 6677 &
START "ZMQ_OUT_PROXY" /MIN %PATH_TO_MONICA_BIN_DIR%\monica-zmq-proxy -pps -f 7788 -b 7777 &

START "ZMQ_MONICA_1" /MIN %PATH_TO_MONICA_BIN_DIR%\monica-zmq-server -ci -i tcp://localhost:6677 -co -o tcp://localhost:7788
START "ZMQ_MONICA_2" /MIN %PATH_TO_MONICA_BIN_DIR%\monica-zmq-server -ci -i tcp://localhost:6677 -co -o tcp://localhost:7788
START "ZMQ_MONICA_3" /MIN %PATH_TO_MONICA_BIN_DIR%\monica-zmq-server -ci -i tcp://localhost:6677 -co -o tcp://localhost:7788
START "ZMQ_MONICA_4" /MIN %PATH_TO_MONICA_BIN_DIR%\monica-zmq-server -ci -i tcp://localhost:6677 -co -o tcp://localhost:7788
START "ZMQ_MONICA_5" /MIN %PATH_TO_MONICA_BIN_DIR%\monica-zmq-server -ci -i tcp://localhost:6677 -co -o tcp://localhost:7788