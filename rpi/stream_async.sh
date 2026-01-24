rm PID.txt nohup.out

nohup bash stream.sh &
echo $! > PID.txt