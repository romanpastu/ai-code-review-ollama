To play with the source.

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

To compile the source.

pyinstaller --onefile script.py

To deploy the compiled source
./review_deploy.sh