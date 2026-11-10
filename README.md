# DistillationDigitalTwin
Running the Distillation Model}\label{app:run}
The notebook runs in a Jupyter environment such as VS Code with the Jupyter extension. It was tested with Python 3.14.2, numpy 2.5.4, pandas 3.0.6, openpyxl 3.1.5, scipy 1.18.1 and matplotlib 3.11.2. The project folder already contains this environment in .venv. On another computer it can be created in the project folder with the following commands:

\begin{verbatim}
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install numpy pandas openpyxl scipy matplotlib ipykernel
\end{verbatim}

The model is then run as follows:

\begin{enumerate}
\item Place the notebook and the workbook in the same folder and open distDigTwin.ipynb.
\item Select the .venv environment as the notebook kernel.
\item Adjust the settings in the second cell if required (Table~\ref{tab:5}).
\item Close results/results\_all\_tabs.xlsx if it is open in Excel, because an open file cannot be overwritten.
\item Choose \textbf{Restart} and then \textbf{Run All}. A full run takes about 10 seconds.
\end{enumerate}
The kernel must be restarted after a change in the settings, and all cells must be run. Some settings are stored when the functions are defined, so running only the last cells would use the old values. Each full run overwrites the previous results, so results to be kept must be copied first.
