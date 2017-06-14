u = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
l = 'abcdefghijklmnopqrstuvwxyz'

res = [''] * len(u) * 2
res[::4] = u[::2]
res[1::4] = u[1::2]
res[2::4] = l[::2]
res[3::4] = l[1::2]
print(''.join(res))
