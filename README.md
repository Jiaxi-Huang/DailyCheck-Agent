# DailyCheck-Agent
A GUI-based agent to help you stay consistent with daily check-ins. Perfect for tracking habits, tasks, or goals with an intuitive interface and customizable features.

## Tutorial
### Installation
```bash
# Clone the repository
git clone https://github.com/Jiaxi-Huang/DailyCheck-Agent.git
# Install Scrcpy
# You can also download it manually
curl -L -o scrcpy-macos-aarch64-v3.3.4.tar.gz https://github.com/Genymobile/scrcpy/releases/download/v3.3.4/scrcpy-macos-aarch64-v3.3.4.tar.gz && \
tar -xzvf scrcpy-macos-aarch64-v3.3.4.tar.gz && \
rm -r scrcpy-macos-aarch64-v3.3.4.tar.gz && \
mv scrcpy-* scrcpy
```
### API Configuration
`model` and `api-key` need to be configured in `config/api.yml`
Now we only support [OpenRouter](https://openrouter.ai/) and [Siliconflow](https://cloud.siliconflow.cn/)
### Tasks Configuration
`tasks.yml` needs to be configured to define task which specify the target app, expected UI flow, key elements to look for, and completion criteria.
### Run
Simply enter terminal and run
```bash
# make sure you are in DailyCheck-Agent folder
chmod +x run.sh 
./run.sh
```

## TODO
- [ ] 
## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.