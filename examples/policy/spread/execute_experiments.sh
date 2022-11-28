mkdir -p {high_cores,high_gflops,agent}
rm -f agent.model {high_cores,high_gflops,agent}/* 
irmasim options_high_cores.json 
irmasim options_high_gflops.json 
irmasim -nr 100 -im agent.model -om agent.model options_agent.json 
