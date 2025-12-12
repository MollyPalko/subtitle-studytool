from mpi4py import MPI
# --- Test MPI ---
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

print(f"[Rank {rank}/{size}] MPI initialized successfully.")

# Now import Okt
from konlpy.tag import Okt
okt = Okt()
print(okt.morphs("테스트 문장입니다."))

