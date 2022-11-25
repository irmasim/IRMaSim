mkdir -p {low_power,high_gflops,agent}
rm -f agent.model {low_power,high_gflops,agent}/* 
irmasim options_low_power.json 
irmasim options_high_gflops.json 
irmasim -nr 10 -im agent.model -om agent.model options_agent.json 
