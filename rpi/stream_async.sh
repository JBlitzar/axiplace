rm -f PID.txt nohup.out

nohup bash stream.sh > nohup.out 2>&1 &
echo $! > PID.txt