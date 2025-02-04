# 추가로 알아야하는 정보 
# 1) 호스팅 제공업체를 알아야함.(green hosting)
# 2) 실제 트래픽: 웹 서버 로그를 통해 (재방문자까지), CDN 통계, 분석 도구를 통해
# 3) 정확한 캐시 비율을 파악하려면 사용자 브라우저 측의 데이터를 세밀하게 수집해야함
#   - 불가능하다면, 통계가 필요한데,  
# (브라우저 로컬 캐시인지, CDN 캐싱인지, 프록시 서버 캐싱인지 등 다양한 형태)
## GDPR 등 개인정보보호 규제를 고려해야 하고, 구현 난이도가 높습니다.
## -방문자 비율 Google Analytics 
## -캐시 적중률 서버 액세스로그, AWS  CloudFront Report

# carbon Intensity (gCO2e/kWh) (We will need to electricity map's API CALL Functions..)
KOREA_AVERAGE_INTENSITY = 407
WORLD_AVERAGE_INTENSITY = 494

#OPERATION WATT (kWh/GB)
ELECTRICITY_DATA_CENTER_O = 0.055  
ELECTRICITY_NETWORK_O = 0.059
ELECTRICITY_USER_DEVICE = 0.080
#EMBODIED WATT (kWh/GB)
ELECTRICITY_EMBODIED = 0.012
ELECTRICITY_EMBODIED_NETWORK = 0.013
ELECTRICITY_EMBODIED_USER_DEVICE = 0.081

# OPERATION EMISSIONS (kWh/GB)
def calculate_operation_emissions(data_transmission_traffic):
    datacenter_o = data_transmission_traffic * ELECTRICITY_DATA_CENTER_O * KOREA_AVERAGE_INTENSITY
    network_o = data_transmission_traffic * ELECTRICITY_NETWORK_O * KOREA_AVERAGE_INTENSITY
    user_device_o = data_transmission_traffic * ELECTRICITY_USER_DEVICE * KOREA_AVERAGE_INTENSITY

    operation_emissions = datacenter_o + network_o + user_device_o

    return datacenter_o, network_o, user_device_o

# Green hosting adjustment
def adjust_for_green_hosting(op_dc, green_host_factor):
    # 실제 반영: op_dc * (1 - green_host_factor)
    # op_dc가 데이터 센터 운영 배출량이므로
    return op_dc * (1 - green_host_factor)

# EMBODIED EMISSIONS (kWh/GB)
def calculate_embodied_emissions(data_transmission_traffic):
    embodied_o = data_transmission_traffic * ELECTRICITY_EMBODIED * KOREA_AVERAGE_INTENSITY
    network_o = data_transmission_traffic * ELECTRICITY_EMBODIED_NETWORK * KOREA_AVERAGE_INTENSITY
    user_device_o = data_transmission_traffic * ELECTRICITY_EMBODIED_USER_DEVICE * KOREA_AVERAGE_INTENSITY

    embodied_emissions = embodied_o + network_o + user_device_o
    return embodied_o, network_o, user_device_o


def estimate_emission_per_page(
    data_gb,
    new_visitor_ratio=1.0,
    return_visitor_ratio=0.0,
    data_cache_ratio=0.0,
    green_host_factor=0.0,
    ):
    # 1) 운영 배출
    op_dc, op_net, op_ud = calculate_operation_emissions(data_gb, carbon_intensity)
    # 2) 내재 배출
    em_dc, em_net, em_ud = calculate_embodied_emissions(data_gb, carbon_intensity)
    
    # 데이터 센터 운영 배출에서 그린호스팅 비율 적용
    op_dc_adjusted = adjust_for_green_hosting(op_dc, green_host_factor)

     # 모든 세그먼트의 합 (운영+내재)
    total_segment_emission = (op_dc_adjusted + em_dc) + (op_net + em_net) + (op_ud + em_ud)

    # 신방문자 부분
    new_visitor_emission = total_segment_emission * new_visitor_ratio

    # 재방문자 부분 (캐시를 통해 일부 전송량이 줄어든다고 가정)
    return_visitor_emission = total_segment_emission * return_visitor_ratio * (1 - data_cache_ratio)

    return new_visitor_emission + return_visitor_emission
