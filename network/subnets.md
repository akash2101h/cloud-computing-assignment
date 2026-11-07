# Subnet allocation for 10.20.0.0/16

Rule: usable hosts = 2^(32 - prefix) - 2. Allocate from the largest requirement to the smallest, each subnet right after the previous one, using the smallest prefix that fits.

## Working

| Subnet | Hosts needed | Smallest block | Prefix | Check |
|---|---|---|---|---|
| app | 1,000 | 2^10 = 1024 addresses | /22 | 1024 - 2 = 1022 >= 1000 (a /23 gives only 510) |
| public | 250 | 2^8 = 256 addresses | /24 | 256 - 2 = 254 >= 250 (a /25 gives only 126) |
| data | 100 | 2^7 = 128 addresses | /25 | 128 - 2 = 126 >= 100 (a /26 gives only 62) |
| management | 20 | 2^5 = 32 addresses | /27 | 32 - 2 = 30 >= 20 (a /28 gives only 14) |

Placement:
- app starts at 10.20.0.0 and spans 1024 addresses, so it ends at 10.20.3.255.
- public starts at 10.20.4.0 and spans 256 addresses, so it ends at 10.20.4.255.
- data starts at 10.20.5.0 and spans 128 addresses, so it ends at 10.20.5.127.
- management starts at 10.20.5.128 and spans 32 addresses, so it ends at 10.20.5.159.

## Result

| Subnet | Network address | Prefix | Usable host range | Broadcast | Usable hosts |
|---|---|---|---|---|---|
| app | 10.20.0.0 | /22 | 10.20.0.1 - 10.20.3.254 | 10.20.3.255 | 1022 |
| public | 10.20.4.0 | /24 | 10.20.4.1 - 10.20.4.254 | 10.20.4.255 | 254 |
| data | 10.20.5.0 | /25 | 10.20.5.1 - 10.20.5.126 | 10.20.5.127 | 126 |
| management | 10.20.5.128 | /27 | 10.20.5.129 - 10.20.5.158 | 10.20.5.159 | 30 |

## NACL explanation

A NACL is stateless: it does not remember that an outgoing request is linked to an incoming reply. Every packet is checked on its own against the rules of its direction, so reply traffic needs its own rules. Here, replies from the app subnet come back inbound on ephemeral ports 1024-65535 (inbound rule 140), and replies to clients go out on their ephemeral ports (outbound rule 110).

Rules are evaluated from the lowest number upward, and the first match decides. The deny for 198.51.100.0/24 is rule 100, below the allows for ports 80 and 443 (110 and 120). If the deny had a higher number, a packet from that range to port 443 would match the allow first and be let in, so the block would have no effect.
