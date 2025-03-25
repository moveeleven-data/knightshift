@echo off
echo Running KnightShift Pipeline...
docker run --rm --env-file "C:\Users\KV-62\Desktop\knightshift\.env.docker" knightshift-pipeline >> "C:\Users\KV-62\Desktop\knightshift\log.txt" 2>&1
echo Done.
pause
